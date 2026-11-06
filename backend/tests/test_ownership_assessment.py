from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.db import get_db
from fastapi import HTTPException, Request

from app.core.authentication import (
    AuthenticatedSession,
    current_session,
    csrf_session,
)


@pytest.fixture
def ownership_client():
    db = MagicMock()

    identity = {"user_id": None}
    csrf_value = "synthetic-ownership-test-csrf"

    def override_get_db():
        yield db

    def override_current_session():
        if identity["user_id"] is None:
            raise HTTPException(
                status_code=401,
                detail="Authentication required",
            )

        return AuthenticatedSession(
            token_digest="synthetic-session-digest",
            csrf_token=csrf_value,
            user={"id": identity["user_id"]},
        )

    def override_csrf_session(request: Request):
        session = override_current_session()

        if request.headers.get("X-CSRF-Token") != csrf_value:
            raise HTTPException(
                status_code=403,
                detail="Invalid CSRF token",
            )

        return session

    previous_overrides = app.dependency_overrides.copy()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_session] = override_current_session
    app.dependency_overrides[csrf_session] = override_csrf_session

    try:
        with TestClient(
            app,
            base_url="https://testserver",
        ) as client:

            def authenticate_as(user_id):
                identity["user_id"] = user_id
                return csrf_value

            yield client, db, authenticate_as

    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)

def test_anonymous_prediction_read_rejected(ownership_client):
    client, db, _ = ownership_client

    response = client.get("/assessment/predictions/101")

    assert response.status_code == 401
    db.execute.assert_not_called()


def test_owner_can_read_prediction(ownership_client):
    client, db, authenticate_as = ownership_client
    authenticate_as(1)

    db.execute.return_value.first.return_value = SimpleNamespace(
        id=101,
        user_id=1,
        match_id=20,
        predicted_winner_id=5,
    )

    response = client.get("/assessment/predictions/101")

    assert response.status_code == 200
    assert response.json()["user_id"] == 1

    sql = str(db.execute.call_args.args[0])
    params = db.execute.call_args.args[1]

    assert "user_id = :user_id" in sql
    assert params["user_id"] == 1
    assert params["prediction_id"] == 101


def test_other_user_prediction_read_rejected(ownership_client):
    client, db, authenticate_as = ownership_client
    authenticate_as(2)

    # Simulate a database ownership-filtered lookup.
    db.execute.return_value.first.return_value = None

    response = client.get("/assessment/predictions/101")

    assert response.status_code == 404

    sql = str(db.execute.call_args.args[0])
    params = db.execute.call_args.args[1]

    assert "user_id = :user_id" in sql
    assert params["user_id"] == 2
    db.commit.assert_not_called()


def test_other_user_prediction_write_rejected(ownership_client):
    client, db, authenticate_as = ownership_client
    csrf_token = authenticate_as(2)

    # Simulate an UPDATE matching zero owned rows.
    db.execute.return_value.first.return_value = None

    response = client.patch(
        "/assessment/predictions/101",
        json={"predicted_winner_id": 6},
        headers={"X-CSRF-Token": csrf_token},
    )

    assert response.status_code == 404

    sql = str(db.execute.call_args.args[0])
    params = db.execute.call_args.args[1]

    assert "up.user_id = :user_id" in sql
    assert params["user_id"] == 2
    assert params["prediction_id"] == 101

    db.commit.assert_not_called()
    db.rollback.assert_called_once()


def test_owner_can_update_prediction(ownership_client):
    client, db, authenticate_as = ownership_client
    csrf_token = authenticate_as(1)

    db.execute.return_value.first.return_value = SimpleNamespace(
        id=101,
        user_id=1,
        match_id=20,
        predicted_winner_id=6,
    )

    response = client.patch(
        "/assessment/predictions/101",
        json={"predicted_winner_id": 6},
        headers={"X-CSRF-Token": csrf_token},
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == 1
    assert response.json()["predicted_winner_id"] == 6

    db.commit.assert_called_once()


def test_prediction_write_without_csrf_rejected(ownership_client):
    client, db, authenticate_as = ownership_client
    authenticate_as(1)

    response = client.patch(
        "/assessment/predictions/101",
        json={"predicted_winner_id": 6},
    )

    assert response.status_code == 403

    db.execute.assert_not_called()
    db.commit.assert_not_called()

def test_revoked_session_cannot_read_prediction(ownership_client):
    client, db, authenticate_as = ownership_client

    authenticate_as(1)
    app.dependency_overrides[current_session] = (
        lambda: (_ for _ in ()).throw(
            HTTPException(
                status_code=401,
                detail="Authentication required",
            )
        )
    )

    response = client.get(
        "/assessment/predictions/101"
    )

    assert response.status_code == 401
    db.execute.assert_not_called()