import hashlib
import json
import os
from pathlib import Path

for key, value in {"DATABASE_HOST": "localhost", "DATABASE_PORT": "5432", "DATABASE_NAME": "test_db", "DATABASE_USER": "test_user", "DATABASE_PASSWORD": "test_password"}.items():
    os.environ.setdefault(key, value)

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.main import app
from app.core.config import settings
from app.database.db import get_db
from app.ml.evaluation.market_audit import distribution_metrics, evaluate_sport
from app.services.ml_insights import match_inputs, read_evaluation
from app.services.prediction_service import MatchNotFoundError


def test_confusion_orientation_and_calibration_include_100_percent():
    classes = ["away_win", "draw", "home_win"]
    actual = ["away_win", "home_win", "draw", "home_win"]
    probabilities = [[1, 0, 0], [.6, .1, .3], [.1, .6, .3], [.1, .2, .7]]
    metrics = distribution_metrics(actual, probabilities, classes)
    assert metrics["correct"] == 3
    assert metrics["confusion_matrix"] == [[1, 0, 0], [0, 1, 0], [1, 0, 1]]
    assert sum(b["count"] for b in metrics["calibration_bins"]) == 4
    assert metrics["calibration_bins"][9]["count"] == 1
    assert metrics["calibration_bins"][6]["accuracy"] == .5
    assert metrics["expected_calibration_error"] == pytest.approx(.125)


@pytest.mark.parametrize("probabilities", [[[.5, .6]], [[float("nan"), .5]], [[-1, 2]]])
def test_invalid_probabilities_are_rejected(probabilities):
    with pytest.raises(ValueError):
        distribution_metrics(["home_win"], probabilities, ["away_win", "home_win"])


def test_changed_snapshot_is_not_presented_as_saved_model_evaluation():
    games = pd.DataFrame([dict(game_id=str(i), game_date=f"2026-01-{i+1:02}", home_team="A", away_team="B", home_score=i % 3, away_score=1) for i in range(10)])
    with pytest.raises(ValueError, match="differ from this model"):
        evaluate_sport(games, "NFL", {"dataset_sha256": "wrong"}, {}, pd.Timestamp("2026-02-01", tz="UTC"))


@pytest.fixture
def history_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    with Session(engine) as db:
        for sql in ["CREATE TABLE leagues(id INTEGER PRIMARY KEY, abbreviation TEXT)",
                    "CREATE TABLE teams(id INTEGER PRIMARY KEY, name TEXT)",
                    "CREATE TABLE matches(id INTEGER PRIMARY KEY, league_id INTEGER, home_team_id INTEGER, away_team_id INTEGER, start_time TIMESTAMP, status TEXT, home_score INTEGER, away_score INTEGER)",
                    "INSERT INTO leagues VALUES(1,'EPL')", "INSERT INTO teams VALUES(1,'Home'),(2,'Away')",
                    "INSERT INTO matches VALUES(1,1,1,2,'2026-01-01 12:00:00','final',3,1),(2,1,2,1,'2026-01-02 12:00:00','final',2,2),(3,1,1,2,'2026-01-03 20:00:00','final',9,0),(4,1,1,2,'2026-01-03 10:00:00','final',7,0),(5,1,1,2,'2026-01-04 12:00:00','final',8,0)"]:
            db.execute(text(sql))
        db.commit()
        yield db


def test_inputs_exclude_target_same_day_and_future_results(history_db):
    before = match_inputs(history_db, 3)
    home, away = before["teams"]
    assert home["history_games"] == away["history_games"] == 2
    assert home["win_rate"] == .5 and away["win_rate"] == 0
    assert home["avg_score"] == 2.5 and away["avg_score"] == 1.5
    assert before["feature_cutoff"] == "2026-01-03T00:00:00+00:00"
    history_db.execute(text("UPDATE matches SET home_score=0,away_score=99 WHERE id>=3"))
    assert match_inputs(history_db, 3) == before
    with pytest.raises(MatchNotFoundError):
        match_inputs(history_db, 999)


def test_historical_inputs_warn_when_deployed_fit_is_later(history_db):
    class LaterRegistry:
        def get(self, sport):
            return None, {"artifact_version": "v1", "train_end": "2026-01-10T00:00:00Z"}
    assert match_inputs(history_db, 3, LaterRegistry())["model"]["eligible_for_target"] is False


def test_stale_or_missing_audit_returns_controlled_503(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MODEL_ODDS_ENABLED", True)
    monkeypatch.setattr(settings, "MARKET_MODEL_DIRECTORY", tmp_path)
    with TestClient(app) as client:
        response = client.get("/insights/audit")
        assert response.status_code == 503
        assert str(tmp_path) not in response.text
        (tmp_path / "manifest.json").write_text("{}")
        (tmp_path / "evaluation.json").write_text(json.dumps({"schema_version": 1, "manifest_sha256": "stale"}))
        assert client.get("/insights/audit").status_code == 503


def test_public_inputs_use_read_only_history_dependency(history_db, monkeypatch):
    monkeypatch.setattr(settings, "MODEL_ODDS_ENABLED", False)
    app.dependency_overrides[get_db] = lambda: history_db
    try:
        with TestClient(app) as client:
            assert client.get("/insights/matches/0/inputs").status_code == 422
            assert client.get("/insights/matches/999/inputs").status_code == 404
            response = client.get("/insights/matches/3/inputs")
            assert response.status_code == 200
            assert response.json()["teams"][0]["avg_score"] == 2.5
            assert history_db.execute(text("SELECT COUNT(*) FROM matches")).scalar_one() == 5
    finally:
        app.dependency_overrides.pop(get_db, None)
