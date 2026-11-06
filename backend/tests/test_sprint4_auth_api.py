from types import SimpleNamespace
from unittest.mock import MagicMock

import bcrypt
import pytest
from fastapi.testclient import TestClient

from app.services import login_throttle
from app.main import app
from app.database.db import get_db
from app.services import session_security


@pytest.fixture
def client():
    password_hash = bcrypt.hashpw(
        b"TestPassword123",
        bcrypt.gensalt(),
    ).decode("utf-8")

    user = SimpleNamespace(
        id=1,
        email="test@example.com",
        username="testuser",
        display_name="Test User",
        is_active=True,
        password_hash=password_hash,
    )

    db = MagicMock()
    db.execute.return_value.first.return_value = user

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(
            app,
            base_url="https://testserver",
        ) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_login_success(client):
    response = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "TestPassword123",
        },
    )

    assert response.status_code == 200
    assert "vigor_session" in client.cookies

    cookie_header = response.headers["set-cookie"].lower()

    assert "httponly" in cookie_header
    assert "secure" in cookie_header
    assert "samesite=lax" in cookie_header


def test_wrong_password_rejected(client):
    response = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "WrongPassword123",
        },
    )

    assert response.status_code == 401


def test_anonymous_access_rejected(client):
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_login_and_protected_access(client):
    login = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "TestPassword123",
        },
    )

    assert login.status_code == 200

    protected = client.get("/auth/me")

    assert protected.status_code == 200
    assert protected.json()["email"] == "test@example.com"


def test_logout_revokes_session(client):
    login = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "TestPassword123",
        },
    )

    assert login.status_code == 200

    csrf_response = client.get("/auth/csrf")
    assert csrf_response.status_code == 200

    csrf_token = csrf_response.json()["csrf_token"]

    logout = client.post(
        "/auth/logout",
        headers={"X-CSRF-Token": csrf_token},
    )

    assert logout.status_code == 200

    protected = client.get("/auth/me")
    assert protected.status_code == 401

def test_logout_rejects_missing_csrf(client):
    login = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "TestPassword123",
        },
    )

    assert login.status_code == 200

    logout = client.post("/auth/logout")

    assert logout.status_code == 403

    protected = client.get("/auth/me")
    assert protected.status_code == 200

def test_login_blocks_sixth_attempt(client):
    email = "test@example.com"
    password = "TestPassword123"

    login_throttle.clear_failures(email)

    try:
        # Five incorrect passwords within the time window
        for attempt in range(5):
            response = client.post(
                "/auth/login",
                json={
                    "email": email,
                    "password": "IncorrectPassword123",
                },
            )

            assert response.status_code == 401, (
                f"Attempt {attempt + 1} should return 401"
            )

        # Even the correct password must be blocked
        blocked_response = client.post(
            "/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )

        assert blocked_response.status_code == 429

        # A blocked attempt must not issue a session
        assert "vigor_session" not in blocked_response.cookies

        # No authenticated session should exist
        protected_response = client.get("/auth/me")
        assert protected_response.status_code == 401

    finally:
        # Keep the test independent of other tests
        login_throttle.clear_failures(email)

def test_logout_rejects_invalid_csrf(client):
    login = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "TestPassword123",
        },
    )

    assert login.status_code == 200

    logout = client.post(
        "/auth/logout",
        headers={
            "X-CSRF-Token": "invalid-csrf-token",
        },
    )

    assert logout.status_code == 403

    protected = client.get("/auth/me")
    assert protected.status_code == 200

def test_logout_rejects_other_session_csrf(client):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(
        app,
        base_url="https://testserver",
    ) as other_client:
        login_a = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPassword123",
            },
        )

        login_b = other_client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPassword123",
            },
        )

        assert login_a.status_code == 200
        assert login_b.status_code == 200

        csrf_b = other_client.get("/auth/csrf")
        assert csrf_b.status_code == 200

        stolen_token = csrf_b.json()["csrf_token"]

        logout_a = client.post(
            "/auth/logout",
            headers={"X-CSRF-Token": stolen_token},
        )

        assert logout_a.status_code == 403

        protected_a = client.get("/auth/me")
        assert protected_a.status_code == 200

def test_unknown_account_returns_generic_error(client):
    from app.services import login_throttle
    from app.database.db import get_db

    email = "unknown-user@example.com"

    db = app.dependency_overrides[get_db]
    original_override = db

    from unittest.mock import MagicMock

    mock_db = MagicMock()
    mock_db.execute.return_value.first.return_value = None

    def override_unknown_user_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_unknown_user_db

    login_throttle.clear_failures(email)

    try:
        response = client.post(
            "/auth/login",
            json={
                "email": email,
                "password": "WrongPassword123",
            },
        )

        assert response.status_code == 401
        assert response.json() == {
            "detail": "Invalid email or password"
        }
        assert "vigor_session" not in response.cookies

    finally:
        app.dependency_overrides[get_db] = original_override
        login_throttle.clear_failures(email)

def test_unknown_account_runs_dummy_password_check(client, monkeypatch):
    from app.database.db import get_db
    import app.routes.auth as auth_module

    original_override = app.dependency_overrides[get_db]
    observed_hashes = []

    def override_missing_user():
        from unittest.mock import MagicMock

        db = MagicMock()
        db.execute.return_value.first.return_value = None
        yield db

    original_verify = auth_module.verify_password

    def spy_verify_password(password, stored_hash):
        observed_hashes.append(stored_hash)
        return original_verify(password, stored_hash)

    app.dependency_overrides[get_db] = override_missing_user
    monkeypatch.setattr(
        auth_module,
        "verify_password",
        spy_verify_password,
    )

    try:
        response = client.post(
            "/auth/login",
            json={
                "email": "missing-account@example.com",
                "password": "WrongPassword123",
            },
        )

        assert response.status_code == 401
        assert observed_hashes == [
            auth_module.DUMMY_PASSWORD_HASH
        ]
    finally:
        app.dependency_overrides[get_db] = original_override