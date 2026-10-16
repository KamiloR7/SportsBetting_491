"""Sprint 3 - S3-01.04: Kickoff-safe feature integration tests."""

import pandas as pd
import pytest

from app.ml.features.kickoff_safe_features import (
    create_kickoff_safe_features,
)


def sample_games():
    """Create two synthetic games with valid timestamps."""

    return pd.DataFrame([
        {
            "game_id": "GAME-001",
            "game_date": "2026-01-01",
            "home_team": "Team A",
            "away_team": "Team B",
            "home_score": 3,
            "away_score": 1,
            "start_time": "2026-01-01T19:00:00Z",
            "feature_as_of": "2026-01-01T18:00:00Z",
            "result_available_at": "2026-01-01T22:00:00Z",
        },
        {
            "game_id": "GAME-002",
            "game_date": "2026-01-02",
            "home_team": "Team B",
            "away_team": "Team A",
            "home_score": 2,
            "away_score": 0,
            "start_time": "2026-01-02T19:00:00Z",
            "feature_as_of": "2026-01-02T18:00:00Z",
            "result_available_at": "2026-01-02T22:00:00Z",
        },
    ])


def test_valid_historical_features():
    """Completed earlier games may contribute to later features."""

    features = create_kickoff_safe_features(sample_games())

    assert len(features) == 2
    assert features.loc[0, "home_win_rate"] == 0.0
    assert features.loc[1, "away_win_rate"] == 1.0


def test_rejects_features_after_kickoff():
    """A prediction must not use features generated after kickoff."""

    games = sample_games()

    games.loc[1, "feature_as_of"] = "2026-01-02T20:00:00Z"

    with pytest.raises(ValueError, match="before match kickoff"):
        create_kickoff_safe_features(games)


def test_rejects_future_historical_results():
    """Previous-day results unavailable at prediction time must be rejected."""

    games = sample_games()

    # The first game's result is not available until after
    # the second game's prediction timestamp.
    games.loc[0, "result_available_at"] = "2026-01-03T00:00:00Z"

    with pytest.raises(ValueError, match="unavailable at prediction time"):
        create_kickoff_safe_features(games)


def test_rejects_missing_timestamp_columns():
    """Required timestamps cannot be omitted."""

    games = sample_games().drop(columns=["feature_as_of"])

    with pytest.raises(ValueError, match="Missing timestamp columns"):
        create_kickoff_safe_features(games)


def test_rejects_result_before_kickoff():
    """A completed game's result cannot predate its kickoff."""

    games = sample_games()

    games.loc[0, "result_available_at"] = "2026-01-01T18:00:00Z"

    with pytest.raises(ValueError, match="predates match kickoff"):
        create_kickoff_safe_features(games)