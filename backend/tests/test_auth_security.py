"""U1.1-U1.4 against real routes, sessions, bcrypt and isolated databases.

PostgreSQL requires an explicit localhost-only disposable test database URL.
CI sets SPRINT4_REQUIRE_POSTGRES=1 so missing integration configuration fails.
"""

import os
from pathlib import Path
from uuid import uuid4

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, insert, select, text, update
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

for name, value in {
    "DATABASE_HOST": "localhost", "DATABASE_PORT": "5432",
    "DATABASE_NAME": "test_db", "DATABASE_USER": "test_user",
    "DATABASE_PASSWORD": "test_password",
}.items():
    os.environ.setdefault(name, value)

from app.core.authentication import CHALLENGE_COOKIE, SESSION_COOKIE, digest, now_seconds
from app.core.config import settings
from app.core.passwords import hash_password
from app.database.auth_tables import (
    assessment_records, attempts, initialize_auth_tables, sessions, users,
)
from app.database.db import get_db
from app.main import app

PASSWORD = "SyntheticPassword123!"


@pytest.fixture(scope="session")
def synthetic_password_hash():
    return hash_password(PASSWORD)


@pytest.fixture(params=["sqlite", "postgres"])
def auth_database(request):
    if request.param == "sqlite":
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        users.create(engine)
        initialize_auth_tables(engine)
        try:
            yield engine
        finally:
            engine.dispose()
        return
    value = os.environ.get("SPRINT4_TEST_DATABASE_URL")
    allowed = os.environ.get("SPRINT4_ALLOW_DISPOSABLE_TEST") == "1"
    if not value or not allowed:
        if os.environ.get("SPRINT4_REQUIRE_POSTGRES") == "1":
            pytest.fail("Required disposable PostgreSQL configuration is missing")
        pytest.skip("Disposable PostgreSQL not explicitly configured")
    url = make_url(value)
    if url.get_backend_name() != "postgresql" or url.database != "sportsbetting_sprint4_test" or url.host not in {"localhost", "127.0.0.1", "::1"}:
        pytest.fail("Only a local sportsbetting_sprint4_test database is permitted")
    schema = "auth_s4_" + uuid4().hex
    bootstrap = create_engine(url)
    engine = None
    try:
        with bootstrap.begin() as conn:
            conn.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
        engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
        ddl = (Path(__file__).parents[1] / "app/database/sports_prediction_schema.sql").read_text()
        with engine.begin() as conn:
            conn.exec_driver_sql(ddl.replace("BEGIN;", "").replace("COMMIT;", ""))
        initialize_auth_tables(engine)
        yield engine
    finally:
        if engine is not None:
            engine.dispose()
        with bootstrap.begin() as conn:
            conn.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        bootstrap.dispose()


@pytest.fixture
def harness(auth_database, synthetic_password_hash, monkeypatch):
    factory = sessionmaker(bind=auth_database)
    with auth_database.begin() as conn:
        conn.execute(insert(users), [
            {"email": "alice@example.com", "password_hash": synthetic_password_hash, "is_active": True},
            {"email": "bob@example.com", "password_hash": synthetic_password_hash, "is_active": True},
        ])
        conn.execute(insert(assessment_records), [
            {"id": 1, "owner_id": 1, "note": "Alice synthetic note"},
            {"id": 2, "owner_id": 2, "note": "Bob synthetic note"},
        ])
    clock = [1_000_000.0]

    def database():
        with factory() as db:
            yield db

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[now_seconds] = lambda: clock[0]
    monkeypatch.setattr(settings, "AUTH_ASSESSMENT_ENABLED", True)
    with TestClient(app, base_url="https://testserver") as client:
        yield client, clock, auth_database
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous)


def login(client, email="alice@example.com", password=PASSWORD):
    # The pre-login challenge also prevents login CSRF. Each success consumes it.
    client.cookies.delete(SESSION_COOKIE)
    token = client.get("/auth/csrf").json()["csrf_token"]
    return client.post("/auth/login", json={"email": email, "password": password}, headers={"X-CSRF-Token": token})


def csrf(client):
    return {"X-CSRF-Token": client.get("/auth/csrf").json()["csrf_token"]}


def snapshot_records(engine):
    with engine.connect() as conn:
        return [tuple(row) for row in conn.execute(select(assessment_records).order_by(assessment_records.c.id))]


PROTECTED = [
    ("GET", "/auth/me", None),
    ("POST", "/auth/logout", None),
    ("GET", "/auth/assessment/records/1", None),
    ("PATCH", "/auth/assessment/records/1", {"note": "changed"}),
]


@pytest.mark.parametrize("method,path,body", PROTECTED)
@pytest.mark.parametrize("state", ["anonymous", "tampered", "expired", "logged_out"])
def test_u11_every_protected_route_denies_bad_sessions_without_writes(harness, method, path, body, state):
    client, clock, engine = harness
    if state != "anonymous":
        assert login(client).status_code == 200
        token = client.cookies.get(SESSION_COOKIE)
        if state == "tampered":
            client.cookies.clear()
            client.cookies.set(SESSION_COOKIE, token[:-1] + ("A" if token[-1] != "A" else "B"))
        elif state == "expired":
            clock[0] += 1800
        else:
            assert client.post("/auth/logout", headers=csrf(client)).status_code == 204
            client.cookies.set(SESSION_COOKIE, token)
    before = snapshot_records(engine)
    result = client.request(method, path, json=body)
    assert result.status_code == 401
    assert snapshot_records(engine) == before


def test_u11_authorized_requests_and_public_routes(harness):
    client, _, engine = harness
    assert client.get("/health").status_code == 200
    assert login(client).status_code == 200
    assert client.get("/auth/me").json()["email"] == "alice@example.com"
    assert client.get("/auth/assessment/records/1").json()["note"] == "Alice synthetic note"
    response = client.patch("/auth/assessment/records/1", json={"note": "authorized write"}, headers=csrf(client))
    assert response.status_code == 200
    assert snapshot_records(engine)[0][-1] == "authorized write"
    assert client.post("/auth/logout", headers=csrf(client)).status_code == 204


def test_u12_password_login_expiry_and_server_side_storage(harness):
    client, clock, engine = harness
    wrong = login(client, password="WrongSyntheticPassword")
    missing = login(client, email="missing@example.com")
    assert wrong.status_code == missing.status_code == 401
    assert wrong.json() == missing.json() == {"detail": "Invalid email or password."}
    assert login(client, email="ALICE@example.com").status_code == 200
    token = client.cookies.get(SESSION_COOKIE)
    with engine.connect() as conn:
        stored = conn.execute(select(sessions)).mappings().one()
        assert stored["token_digest"] == digest(token) != token
        assert stored["expires_at"] == clock[0] + 1800
    clock[0] += 1799
    assert client.get("/auth/me").status_code == 200
    clock[0] += 1
    assert client.get("/auth/me").status_code == 401


def test_u12_logout_replay_and_session_rotation(harness):
    client, _, engine = harness
    assert login(client).status_code == 200
    old = client.cookies.get(SESSION_COOKIE)
    # Re-authenticate without the test helper clearing the previous session.
    client.cookies.delete(SESSION_COOKIE)
    challenge = client.get("/auth/csrf").json()["csrf_token"]
    client.cookies.set(SESSION_COOKIE, old, domain="testserver.local", path="/")
    assert client.post("/auth/login", json={"email": "alice@example.com", "password": PASSWORD}, headers={"X-CSRF-Token": challenge}).status_code == 200
    new = client.cookies.get(SESSION_COOKIE)
    assert old != new
    with engine.connect() as conn:
        assert conn.execute(select(sessions).where(sessions.c.token_digest == digest(old))).first() is None
    assert client.post("/auth/logout", headers=csrf(client)).status_code == 204
    client.cookies.clear()
    client.cookies.set(SESSION_COOKIE, new)
    assert client.get("/auth/me").status_code == 401


@pytest.mark.parametrize("method,path,body", [PROTECTED[1], PROTECTED[3]])
@pytest.mark.parametrize("token", [None, "invalid"])
def test_u13_missing_invalid_csrf_denies_state_changes(harness, method, path, body, token):
    client, _, engine = harness
    assert login(client).status_code == 200
    before = snapshot_records(engine)
    result = client.request(method, path, json=body, headers={"X-CSRF-Token": token} if token else {})
    assert result.status_code == 403
    assert snapshot_records(engine) == before
    assert client.get("/auth/me").status_code == 200


def test_u13_cross_account_read_write_and_token_binding(harness):
    client, _, engine = harness
    assert login(client, email="bob@example.com").status_code == 200
    bob_csrf = csrf(client)["X-CSRF-Token"]
    before = snapshot_records(engine)
    read = client.get("/auth/assessment/records/1")
    write = client.patch("/auth/assessment/records/1", json={"note": "forbidden"}, headers=csrf(client))
    assert read.status_code == write.status_code == 403
    assert "Alice synthetic note" not in read.text + write.text
    assert snapshot_records(engine) == before
    assert login(client).status_code == 200
    assert client.patch("/auth/assessment/records/1", json={"note": "forbidden"}, headers={"X-CSRF-Token": bob_csrf}).status_code == 403
    assert snapshot_records(engine) == before


def test_u13_cookie_flags_login_csrf_and_cross_origin(harness):
    client, _, _ = harness
    assert client.post("/auth/login", json={"email": "alice@example.com", "password": PASSWORD}).status_code == 403
    response = login(client)
    cookie = next(value for value in response.headers.get_list("set-cookie") if value.startswith(SESSION_COOKIE + "="))
    assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=strict" in cookie
    assert "Max-Age=1800" in cookie and "Path=/" in cookie and "Domain=" not in cookie
    assert response.headers["cache-control"] == "no-store"
    for origin in ["https://evil.example", "null"]:
        assert client.post("/auth/logout", headers={**csrf(client), "Origin": origin}).status_code == 403
    assert client.post("/auth/logout", headers={**csrf(client), "Sec-Fetch-Site": "cross-site"}).status_code == 403
    client.base_url = "http://testserver"
    assert client.get("/auth/csrf").status_code == 403
    assert client.get("/auth/me").status_code == 403
    assert client.post("/auth/register", json={"email": "new@example.com", "password": PASSWORD}).status_code == 403


def test_u14_threshold_account_key_and_recovery(harness):
    client, clock, engine = harness
    for _ in range(5):
        assert login(client, password="WrongSyntheticPassword").status_code == 401
    blocked = login(client, email="ALICE@example.com")
    assert blocked.status_code == 429 and blocked.headers["retry-after"] == "900"
    assert login(client, email="bob@example.com").status_code == 200
    clock[0] += 899
    assert login(client).status_code == 429
    clock[0] += 1
    assert login(client).status_code == 200
    with engine.connect() as conn:
        row = conn.execute(select(attempts).where(attempts.c.key_digest == digest("alice@example.com"))).mappings().one()
        assert row["failure_count"] == 0 and row["blocked_until"] == 0


def test_u14_five_minute_boundary_resets_and_success_resets(harness):
    client, clock, _ = harness
    for _ in range(4):
        assert login(client, password="WrongSyntheticPassword").status_code == 401
    clock[0] += 300
    assert login(client, password="WrongSyntheticPassword").status_code == 401
    assert login(client).status_code == 200
    for _ in range(4):
        assert login(client, password="WrongSyntheticPassword").status_code == 401
    assert login(client).status_code == 200
    # Rolling window: the first failure ages out, the next five still count.
    for delay in [0, 299, 2, 1, 1, 1]:
        clock[0] += delay
        assert login(client, password="WrongSyntheticPassword").status_code == 401
    assert login(client).status_code == 429


def test_u14_storage_validation_and_sanitized_logs(harness, caplog):
    client, _, engine = harness
    caplog.set_level("INFO", logger="vigor.security")
    assert login(client, password="WrongSyntheticPassword").status_code == 401
    assert login(client).status_code == 200
    token = client.cookies.get(SESSION_COOKIE)
    csrf_token = csrf(client)["X-CSRF-Token"]
    assert client.post("/auth/logout", headers={"X-CSRF-Token": csrf_token}).status_code == 204
    for secret in [PASSWORD, "WrongSyntheticPassword", token, csrf_token, "alice@example.com"]:
        assert secret not in caplog.text
    assert "event=login_failed" in caplog.text and "event=logout_succeeded" in caplog.text
    with engine.connect() as conn:
        stored = conn.execute(select(users.c.password_hash).where(users.c.id == 1)).scalar_one()
        assert stored != PASSWORD and bcrypt.checkpw(PASSWORD.encode(), stored.encode())
    with engine.begin() as conn:
        conn.execute(update(users).where(users.c.id == 1).values(password_hash="invalid-hash"))
    assert login(client).status_code == 401
    for endpoint in ["/auth/login", "/auth/register"]:
        result = client.post(endpoint, json={"email": "not-an-email", "password": PASSWORD})
        assert result.status_code == 422 and PASSWORD not in result.text
        result = client.post(endpoint, json={"email": "alice@example.com", "password": "é" * 37})
        assert result.status_code == 422 and "é" * 37 not in result.text


def test_disabled_account_and_assessment_default_gate(harness, monkeypatch):
    client, _, engine = harness
    assert login(client).status_code == 200
    with engine.begin() as conn:
        conn.execute(update(users).where(users.c.id == 1).values(is_active=False))
    assert client.get("/auth/me").status_code == 401
    assert login(client).status_code == 401
    monkeypatch.setattr(settings, "AUTH_ASSESSMENT_ENABLED", False)
    assert client.get("/auth/assessment/records/1").status_code == 404


def test_postgres_or_sqlite_registration_to_login_integration(harness):
    client, _, engine = harness
    registered = client.post("/auth/register", json={"email": "new@example.com", "password": PASSWORD})
    assert registered.status_code == 201
    assert PASSWORD not in registered.text and "password_hash" not in registered.text
    assert client.post("/auth/register", json={"email": "new@example.com", "password": PASSWORD}).status_code == 409
    assert client.post("/auth/register", json={"email": "NEW@example.com", "password": PASSWORD}).status_code == 409
    assert login(client, email="new@example.com").status_code == 200
    assert client.get("/auth/me").json()["id"] == registered.json()["id"]


def test_login_challenge_expiry_and_successful_replay_rejected(harness):
    client, clock, _ = harness
    token = client.get("/auth/csrf").json()["csrf_token"]
    clock[0] += 300
    assert client.post("/auth/login", json={"email": "alice@example.com", "password": PASSWORD}, headers={"X-CSRF-Token": token}).status_code == 403
    assert login(client).status_code == 200
    old_csrf = token
    assert client.post("/auth/login", json={"email": "alice@example.com", "password": PASSWORD}, headers={"X-CSRF-Token": old_csrf}).status_code == 403


@pytest.mark.parametrize("auth_database", ["postgres"], indirect=True)
def test_u14_concurrent_failures_share_database_throttle(harness):
    from concurrent.futures import ThreadPoolExecutor

    client, _, engine = harness
    response = client.get("/auth/csrf")
    headers = {
        "X-CSRF-Token": response.json()["csrf_token"],
        "Cookie": f"{CHALLENGE_COOKIE}={client.cookies.get(CHALLENGE_COOKIE)}",
    }

    def attempt(_):
        with TestClient(app, base_url="https://testserver") as other:
            return other.post("/auth/login", json={"email": "alice@example.com", "password": "WrongSyntheticPassword"}, headers=headers).status_code

    with ThreadPoolExecutor(max_workers=7) as pool:
        statuses = sorted(pool.map(attempt, range(7)))
    assert statuses == [401] * 5 + [429] * 2
    with engine.connect() as conn:
        assert conn.execute(select(attempts.c.failure_count).where(attempts.c.key_digest == digest("alice@example.com"))).scalar_one() == 5
