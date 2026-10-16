from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest

from app.services.prediction_service import (
    MatchContext,
    MatchHistoryRepository,
    MatchNotFoundError,
    PredictionService,
    UnsupportedSportError,
)


class FakeModel:
    classes_ = np.array([0, 1])

    def predict_proba(self, features):
        return np.array([[0.25, 0.75]] * len(features))

    def predict(self, features):
        return np.array([1] * len(features))


class FakeRegistry:
    def get(self, sport):
        return FakeModel(), {"sport": sport, "artifact_version": f"{sport.lower()}-v1"}


class FakeRepository:
    def __init__(self, sport):
        self.sport = sport

    def get_context(self, match_id):
        return MatchContext(
            match_id=match_id,
            sport=self.sport,
            home_team_id=10,
            home_team_name="Home Team",
            away_team_id=20,
            away_team_name="Away Team",
            features={
                "home_win_rate": 0.6,
                "away_win_rate": 0.4,
                "home_avg_score": 3.0,
                "away_avg_score": 2.0,
                "home_avg_allowed": 1.0,
                "away_avg_allowed": 2.5,
            },
            home_history_games=5,
            away_history_games=4,
        )


@pytest.mark.parametrize("sport", ["NFL", "MLB", "EPL"])
def test_prediction_service_uses_each_sport_path_and_standard_response(sport):
    response = PredictionService(FakeRegistry(), FakeRepository(sport)).predict(42)

    assert response.sport == sport
    assert response.predicted_outcome == "HOME_WIN"
    assert response.predicted_team_id == 10
    assert response.probabilities.home_win == pytest.approx(0.75)
    assert response.probabilities.not_home_win == pytest.approx(0.25)
    assert response.confidence == pytest.approx(0.75)
    assert response.model_version == f"{sport.lower()}-v1"
    assert response.history.home_games == 5


def test_history_lookup_builds_prior_game_features():
    db = MagicMock()
    selected = SimpleNamespace(
        id=42,
        start_time="2026-10-20T18:00:00Z",
        sport="NFL",
        home_team_id=10,
        home_team_name="Home Team",
        away_team_id=20,
        away_team_name="Away Team",
    )
    games = [
        SimpleNamespace(home_team_id=10, away_team_id=30, home_score=21, away_score=14),
        SimpleNamespace(home_team_id=40, away_team_id=10, home_score=17, away_score=10),
        SimpleNamespace(home_team_id=20, away_team_id=50, home_score=7, away_score=3),
    ]
    first, second = MagicMock(), MagicMock()
    first.first.return_value = selected
    second.all.return_value = games
    db.execute.side_effect = [first, second]

    context = MatchHistoryRepository(db).get_context(42)

    assert context.features == {
        "home_win_rate": 0.5,
        "away_win_rate": 1.0,
        "home_avg_score": 15.5,
        "away_avg_score": 7.0,
        "home_avg_allowed": 15.5,
        "away_avg_allowed": 3.0,
    }
    assert context.home_history_games == 2
    assert context.away_history_games == 1


def test_history_lookup_returns_zero_features_for_cold_start():
    db = MagicMock()
    first, second = MagicMock(), MagicMock()
    first.first.return_value = SimpleNamespace(
        id=7,
        start_time="2026-10-20T18:00:00Z",
        sport="MLB",
        home_team_id=1,
        home_team_name="New Home",
        away_team_id=2,
        away_team_name="New Away",
    )
    second.all.return_value = []
    db.execute.side_effect = [first, second]

    context = MatchHistoryRepository(db).get_context(7)

    assert context.home_history_games == context.away_history_games == 0
    assert set(context.features.values()) == {0.0}


def test_history_lookup_reports_unknown_match():
    db = MagicMock()
    db.execute.return_value.first.return_value = None

    with pytest.raises(MatchNotFoundError, match="999"):
        MatchHistoryRepository(db).get_context(999)


def test_history_lookup_rejects_unsupported_league():
    db = MagicMock()
    db.execute.return_value.first.return_value = SimpleNamespace(
        id=8,
        start_time="2026-10-20T18:00:00Z",
        sport="NBA",
        home_team_id=1,
        home_team_name="Home",
        away_team_id=2,
        away_team_name="Away",
    )

    with pytest.raises(UnsupportedSportError, match="NBA"):
        MatchHistoryRepository(db).get_context(8)
