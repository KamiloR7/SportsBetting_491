import os

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sklearn.linear_model import LogisticRegression
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_HOST", "localhost")
os.environ.setdefault("DATABASE_PORT", "5432")
os.environ.setdefault("DATABASE_NAME", "test_db")
os.environ.setdefault("DATABASE_USER", "test_user")
os.environ.setdefault("DATABASE_PASSWORD", "test_password")

from app.database.db import get_db
from app.main import app
from app.ml.features.engineer_multisport_features import FEATURE_COLUMNS
from app.ml.training.train_multisport_baseline import save_baseline


@pytest.fixture
def client(tmp_path, monkeypatch):
    model_dir = tmp_path / "models"
    monkeypatch.setenv("PREDICTION_MODEL_DIR", str(model_dir))
    features = pd.DataFrame([
        {column: float((row + column_index) % 5 + 1)
         for column_index, column in enumerate(FEATURE_COLUMNS)}
        for row in range(12)
    ])
    model = LogisticRegression(max_iter=1000).fit(features, [row % 2 for row in range(12)])
    for sport in ("NFL", "MLB", "EPL"):
        save_baseline(model, {"sport": sport}, model_dir)

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE leagues (id INTEGER PRIMARY KEY, name TEXT, abbreviation TEXT)")
        conn.exec_driver_sql("CREATE TABLE teams (id INTEGER PRIMARY KEY, name TEXT)")
        conn.exec_driver_sql("""
            CREATE TABLE matches (
                id INTEGER PRIMARY KEY, league_id INTEGER, home_team_id INTEGER,
                away_team_id INTEGER, start_time TEXT, status TEXT,
                home_score INTEGER, away_score INTEGER, neutral_site BOOLEAN
            )
        """)
        for league_id, sport in enumerate(("NFL", "MLB", "EPL"), start=1):
            conn.exec_driver_sql(
                "INSERT INTO leagues VALUES (?, ?, ?)",
                (league_id, sport, sport),
            )
            for index in range(4):
                conn.exec_driver_sql(
                    "INSERT INTO teams VALUES (?, ?)",
                    (league_id * 10 + index, f"{sport} Team {index}"),
                )
            rows = [
                (league_id * 100 + 1, league_id, league_id * 10, league_id * 10 + 2,
                 "2026-10-10T12:00:00+00:00", "final", 2, 1, 0),
                (league_id * 100 + 2, league_id, league_id * 10 + 3, league_id * 10 + 1,
                 "2026-10-11T12:00:00+00:00", "final", 1, 1, 0),
                (league_id * 100 + 3, league_id, league_id * 10, league_id * 10 + 1,
                 "2026-10-20T12:00:00+00:00", "scheduled", None, None, 0),
            ]
            for row in rows:
                conn.exec_driver_sql("INSERT INTO matches VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", row)

    session_factory = sessionmaker(bind=engine)

    def test_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = test_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.mark.parametrize("league_id,sport", [(1, "NFL"), (2, "MLB"), (3, "EPL")])
def test_select_match_review_context_and_run_prediction(client, league_id, sport):
    matches = client.get("/matches", params={"league_id": league_id, "status": "scheduled"})
    assert matches.status_code == 200
    assert len(matches.json()) == 1
    match_id = league_id * 100 + 3
    assert matches.json()[0]["id"] == match_id

    detail = client.get(f"/matches/{match_id}")
    assert detail.status_code == 200
    assert detail.json()["home_team_name"] == f"{sport} Team 0"

    for team_id in (league_id * 10, league_id * 10 + 1):
        history = client.get("/matches/history", params={
            "league_id": league_id, "team_id": team_id, "limit": 3
        })
        assert history.status_code == 200
        assert len(history.json()) == 1
        assert history.json()[0]["status"] == "final"

    response = client.post(f"/predictions/matches/{match_id}")
    assert response.status_code == 200
    prediction = response.json()
    assert prediction["predicted_outcome"] in ({"home_win", "away_win", "draw"} if sport == "EPL" else {"home_win", "away_win"})
    probabilities = [prediction["home_win_probability"], prediction["away_win_probability"]]
    if sport == "EPL":
        probabilities.append(prediction["draw_probability"])
    assert sum(probabilities) == pytest.approx(1.0)
    assert prediction["confidence"] == pytest.approx(max(probabilities))
