from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.db import get_db
from app.services.session_security import (
    create_session,
    create_csrf_token,
    revoke_session,
)


@pytest.fixture
def ownership_client():
    db = MagicMock()

    def override_get_db():
        yield db

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db

    tokens = []

    with TestClient(
        app,
        base_url="https://testserver",
    ) as client:
        def authenticate_as(user_id):
            token = create_session(user_id)
            tokens.append(token)
            client.cookies.set("vigor_session", token)
            return token

        yield client, db, authenticate_as

    for token in tokens:
        revoke_session(token)

    if previous is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous


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
    token = authenticate_as(2)

    csrf_token = create_csrf_token(token)

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
    token = authenticate_as(1)

    csrf_token = create_csrf_token(token)

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

    token = authenticate_as(1)
    revoke_session(token)

    response = client.get(
        "/assessment/predictions/101"
    )

    assert response.status_code == 401
    db.execute.assert_not_called()