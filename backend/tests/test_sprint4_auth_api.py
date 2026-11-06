
"""Sprint 4 API regression tests using the shared authentication system."""

import pytest
from fastapi.testclient import TestClient

from app.core.authentication import SESSION_COOKIE, digest
from app.database.auth_tables import sessions
from app.main import app

from backend.tests.test_auth_security import (
    PASSWORD,
    csrf,
    login,
)

# Reuse the team's disposable SQLite/PostgreSQL fixture.
pytest_plugins = ("backend.tests.test_auth_security",)


def test_login_success(harness):
    client, _, engine = harness

    response = login(client)

    assert response.status_code == 200
    assert client.cookies.get(SESSION_COOKIE)

    cookie = next(
        value for value in response.headers.get_list("set-cookie")
        if value.startswith(SESSION_COOKIE + "=")
    )

    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=strict" in cookie
    assert "Max-Age=1800" in cookie

    token = client.cookies.get(SESSION_COOKIE)

    with engine.connect() as conn:
        stored = conn.execute(sessions.select()).mappings().one()
        assert stored["token_digest"] == digest(token)


def test_wrong_password_rejected(harness):
    client, _, _ = harness

    response = login(
        client,
        password="WrongSyntheticPassword",
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid email or password."
    }


def test_anonymous_access_rejected(harness):
    client, _, _ = harness

    assert client.get("/auth/me").status_code == 401


def test_login_and_protected_access(harness):
    client, _, _ = harness

    assert login(client).status_code == 200

    response = client.get("/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"


def test_logout_revokes_session(harness):
    client, _, _ = harness

    assert login(client).status_code == 200

    response = client.post(
        "/auth/logout",
        headers=csrf(client),
    )

    assert response.status_code == 204
    assert client.get("/auth/me").status_code == 401


def test_logout_rejects_missing_csrf(harness):
    client, _, _ = harness

    assert login(client).status_code == 200

    response = client.post("/auth/logout")

    assert response.status_code == 403
    assert client.get("/auth/me").status_code == 200


def test_login_blocks_sixth_attempt(harness):
    client, _, _ = harness

    for _ in range(5):
        response = login(
            client,
            password="IncorrectPassword123",
        )
        assert response.status_code == 401

    blocked = login(client)

    assert blocked.status_code == 429
    assert client.get("/auth/me").status_code == 401


def test_logout_rejects_invalid_csrf(harness):
    client, _, _ = harness

    assert login(client).status_code == 200

    response = client.post(
        "/auth/logout",
        headers={"X-CSRF-Token": "invalid"},
    )

    assert response.status_code == 403
    assert client.get("/auth/me").status_code == 200


def test_logout_rejects_other_session_csrf(harness):
    client, _, _ = harness

    assert login(client).status_code == 200

    with TestClient(app, base_url="https://testserver") as other:
        assert login(other).status_code == 200

        other_csrf = csrf(other)

        response = client.post(
            "/auth/logout",
            headers=other_csrf,
        )

        assert response.status_code == 403
        assert client.get("/auth/me").status_code == 200


def test_unknown_account_returns_generic_error(harness):
    client, _, _ = harness

    response = login(
        client,
        email="missing-account@example.com",
        password="WrongSyntheticPassword",
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid email or password."
    }
    assert client.cookies.get(SESSION_COOKIE) is None


def test_unknown_account_runs_dummy_password_check(
    harness, monkeypatch
):
    import app.routes.auth_sessions as auth_module

    client, _, _ = harness
    observed_hashes = []

    original_verify = auth_module.verify_password

    def spy_verify_password(password, stored_hash):
        observed_hashes.append(stored_hash)
        return original_verify(password, stored_hash)

    monkeypatch.setattr(
        auth_module,
        "verify_password",
        spy_verify_password,
    )

    response = login(
        client,
        email="missing-account@example.com",
        password="WrongSyntheticPassword",
    )

    assert response.status_code == 401
    assert observed_hashes == [auth_module.DUMMY_HASH]


def test_login_requires_prelogin_csrf(harness):
    client, _, _ = harness

    response = client.post(
        "/auth/login",
        json={
            "email": "alice@example.com",
            "password": PASSWORD,
        },
    )

    assert response.status_code == 403
