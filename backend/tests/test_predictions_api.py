import os

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_HOST", "localhost")
os.environ.setdefault("DATABASE_PORT", "5432")
os.environ.setdefault("DATABASE_NAME", "test_db")
os.environ.setdefault("DATABASE_USER", "test_user")
os.environ.setdefault("DATABASE_PASSWORD", "test_password")

from app.main import app
from app.routes.predictions import prediction_service_dependency
from app.schemas.predictions import (
    PredictionHistory,
    PredictionProbabilities,
    PredictionResponse,
)
from app.services.prediction_service import (
    MatchNotFoundError,
    PredictionUnavailableError,
    UnsupportedSportError,
)


class StubService:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error

    def predict(self, match_id):
        if self.error:
            raise self.error
        return self.result.model_copy(update={"match_id": match_id})


def response():
    return PredictionResponse(
        match_id=1,
        sport="NFL",
        home_team_id=10,
        home_team_name="Home Team",
        away_team_id=20,
        away_team_name="Away Team",
        predicted_outcome="HOME_WIN",
        predicted_team_id=10,
        predicted_team_name="Home Team",
        probabilities=PredictionProbabilities(home_win=0.75, not_home_win=0.25),
        confidence=0.75,
        model_version="nfl-v1",
        history=PredictionHistory(home_games=5, away_games=4),
    )


def client_with(service):
    app.dependency_overrides[prediction_service_dependency] = lambda: service
    return TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


def test_prediction_endpoint_returns_standard_contract():
    result = client_with(StubService(result=response())).post("/predictions", json={"match_id": 42})

    assert result.status_code == 200
    assert result.json() == {
        "match_id": 42,
        "sport": "NFL",
        "home_team_id": 10,
        "home_team_name": "Home Team",
        "away_team_id": 20,
        "away_team_name": "Away Team",
        "predicted_outcome": "HOME_WIN",
        "predicted_team_id": 10,
        "predicted_team_name": "Home Team",
        "probabilities": {"home_win": 0.75, "not_home_win": 0.25},
        "confidence": 0.75,
        "model_version": "nfl-v1",
        "history": {"home_games": 5, "away_games": 4},
    }


def test_prediction_request_validation_rejects_invalid_payloads():
    client = client_with(StubService(result=response()))

    for payload in ({}, {"match_id": 0}, {"match_id": "bad"}, {"match_id": 1, "extra": True}):
        assert client.post("/predictions", json=payload).status_code == 422


def test_prediction_endpoint_maps_controlled_errors():
    cases = [
        (MatchNotFoundError("missing"), 404, "missing"),
        (UnsupportedSportError("NBA"), 422, "NBA"),
        (PredictionUnavailableError("private detail"), 503, "temporarily unavailable"),
    ]
    for error, status, detail in cases:
        result = client_with(StubService(error=error)).post("/predictions", json={"match_id": 1})
        assert result.status_code == status
        assert detail in result.json()["detail"]
