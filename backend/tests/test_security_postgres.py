import os
from datetime import datetime, timezone
import pytest

# Do not run PostgreSQL integration tests in the
# existing build job or without explicit test setup.
if os.getenv("SECURITY_POSTGRES_TESTS") != "1":
    pytest.skip(
        "Requires isolated PostgreSQL security test database",
        allow_module_level=True,
    )

if os.getenv("DATABASE_NAME") != "vigor_security_test":
    pytest.fail(
        "PostgreSQL security tests require vigor_security_test",
        pytrace=False,
    )

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.main import app
from app.database.db import engine, get_db
from app.services.session_security import (
    create_session,
    create_csrf_token,
    revoke_session,
)


@pytest.fixture
def postgres_security_client():
    # Roll back all synthetic records after each test.
    with engine.connect() as connection:
        transaction = connection.begin()
        previous_override = app.dependency_overrides.get(get_db)
        tokens = []

        try:
            user_a = connection.execute(
                text("""
                    INSERT INTO users (email, password_hash)
                    VALUES (:email, :password_hash)
                    RETURNING id
                """),
                {
                    "email": "security-user-a@example.test",
                    "password_hash": "synthetic-test-hash",
                },
            ).scalar_one()

            user_b = connection.execute(
                text("""
                    INSERT INTO users (email, password_hash)
                    VALUES (:email, :password_hash)
                    RETURNING id
                """),
                {
                    "email": "security-user-b@example.test",
                    "password_hash": "synthetic-test-hash",
                },
            ).scalar_one()

            home_team = connection.execute(
                text("""
                    INSERT INTO teams (name)
                    VALUES ('Security Test Home')
                    RETURNING id
                """)
            ).scalar_one()

            away_team = connection.execute(
                text("""
                    INSERT INTO teams (name)
                    VALUES ('Security Test Away')
                    RETURNING id
                """)
            ).scalar_one()

            match_id = connection.execute(
                text("""
                    INSERT INTO matches (
                        home_team_id,
                        away_team_id,
                        start_time,
                        status
                    )
                    VALUES (
                        :home_team,
                        :away_team,
                        :start_time,
                        'scheduled'
                    )
                    RETURNING id
                """),
                {
                    "home_team": home_team,
                    "away_team": away_team,
                    "start_time": datetime.now(timezone.utc),
                },
            ).scalar_one()

            prediction_id = connection.execute(
                text("""
                    INSERT INTO user_predictions (
                        user_id,
                        match_id,
                        predicted_winner_id
                    )
                    VALUES (
                        :user_id,
                        :match_id,
                        :winner_id
                    )
                    RETURNING id
                """),
                {
                    "user_id": user_a,
                    "match_id": match_id,
                    "winner_id": home_team,
                },
            ).scalar_one()

            def override_get_db():
                # SAVEPOINTs protect the outer test transaction
                # even when the API calls commit or rollback.
                with Session(
                    bind=connection,
                    join_transaction_mode="create_savepoint",
                ) as db:
                    yield db

            app.dependency_overrides[get_db] = override_get_db

            ids = {
                "user_a": user_a,
                "user_b": user_b,
                "home_team": home_team,
                "away_team": away_team,
                "prediction_id": prediction_id,
            }

            with TestClient(
                app,
                base_url="https://testserver",
            ) as client:

                def authenticate(user_id):
                    client.cookies.clear()
                    token = create_session(user_id)
                    tokens.append(token)
                    client.cookies.set("vigor_session", token)
                    return token

                yield client, connection, ids, authenticate

        finally:
            for token in tokens:
                revoke_session(token)

            if previous_override is None:
                app.dependency_overrides.pop(get_db, None)
            else:
                app.dependency_overrides[get_db] = previous_override

            if transaction.is_active:
                transaction.rollback()


def test_postgres_owner_can_read(postgres_security_client):
    client, connection, ids, authenticate = postgres_security_client

    authenticate(ids["user_a"])

    response = client.get(
        f"/assessment/predictions/{ids['prediction_id']}"
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == ids["user_a"]


def test_postgres_cross_account_read_denied(
    postgres_security_client,
):
    client, connection, ids, authenticate = postgres_security_client

    authenticate(ids["user_b"])

    response = client.get(
        f"/assessment/predictions/{ids['prediction_id']}"
    )

    assert response.status_code == 404


def test_postgres_cross_account_write_changes_zero_rows(
    postgres_security_client,
):
    client, connection, ids, authenticate = postgres_security_client

    token = authenticate(ids["user_b"])
    csrf_token = create_csrf_token(token)

    before = connection.execute(
        text("""
            SELECT user_id, predicted_winner_id
            FROM user_predictions
            WHERE id = :id
        """),
        {"id": ids["prediction_id"]},
    ).one()

    response = client.patch(
        f"/assessment/predictions/{ids['prediction_id']}",
        json={"predicted_winner_id": ids["away_team"]},
        headers={"X-CSRF-Token": csrf_token},
    )

    assert response.status_code == 404

    after = connection.execute(
        text("""
            SELECT user_id, predicted_winner_id
            FROM user_predictions
            WHERE id = :id
        """),
        {"id": ids["prediction_id"]},
    ).one()

    assert before == after
    assert after.user_id == ids["user_a"]
    assert after.predicted_winner_id == ids["home_team"]


def test_postgres_owner_update_persists_within_transaction(
    postgres_security_client,
):
    client, connection, ids, authenticate = postgres_security_client

    token = authenticate(ids["user_a"])
    csrf_token = create_csrf_token(token)

    response = client.patch(
        f"/assessment/predictions/{ids['prediction_id']}",
        json={"predicted_winner_id": ids["away_team"]},
        headers={"X-CSRF-Token": csrf_token},
    )

    assert response.status_code == 200

    saved_winner = connection.execute(
        text("""
            SELECT predicted_winner_id
            FROM user_predictions
            WHERE id = :id
        """),
        {"id": ids["prediction_id"]},
    ).scalar_one()

    assert saved_winner == ids["away_team"]