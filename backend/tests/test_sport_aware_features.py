"""Tests for Sprint 3 sport-aware feature labels."""

import pandas as pd
import pytest

from app.ml.features.sport_aware_features import (
    create_sport_aware_features,
)


def sample_games():
    return pd.DataFrame([
        {
            "game_id": "g1",
            "game_date": "2026-01-01",
            "home_team": "A",
            "away_team": "B",
            "home_score": 2,
            "away_score": 0,
        },
        {
            "game_id": "g2",
            "game_date": "2026-01-02",
            "home_team": "B",
            "away_team": "A",
            "home_score": 1,
            "away_score": 1,
        },
        {
            "game_id": "g3",
            "game_date": "2026-01-03",
            "home_team": "A",
            "away_team": "B",
            "home_score": 0,
            "away_score": 3,
        },
    ])


@pytest.mark.parametrize("sport", ["NFL", "MLB"])
def test_binary_sports_exclude_ties(sport):
    result = create_sport_aware_features(sample_games(), sport)

    assert result["outcome"].tolist() == [
        "home_win",
        "away_win",
    ]
    assert "g2" not in result["game_id"].tolist()


def test_epl_preserves_three_outcomes():
    result = create_sport_aware_features(sample_games(), "EPL")

    assert result["outcome"].tolist() == [
        "home_win",
        "draw",
        "away_win",
    ]


def test_prior_day_features_do_not_use_current_result():
    result = create_sport_aware_features(sample_games(), "EPL")

    first = result.iloc[0]

    assert first["home_win_rate"] == 0
    assert first["away_win_rate"] == 0
    assert first["home_avg_score"] == 0
    assert first["away_avg_score"] == 0


def test_unsupported_sport_rejected():
    with pytest.raises(ValueError, match="Unsupported sport"):
        create_sport_aware_features(sample_games(), "NBA")