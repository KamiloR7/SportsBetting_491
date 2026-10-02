import pandas as pd
import pytest

from app.ml.features.engineer_multisport_features import chronological_split, create_features


def sample():
    return pd.DataFrame([
        {"game_id": "1", "game_date": "2025-01-01", "home_team": "A", "away_team": "B", "home_score": 2, "away_score": 0},
        {"game_id": "2", "game_date": "2025-01-02", "home_team": "B", "away_team": "A", "home_score": 3, "away_score": 1},
        {"game_id": "3", "game_date": "2025-01-03", "home_team": "A", "away_team": "B", "home_score": 1, "away_score": 0},
        {"game_id": "4", "game_date": "2025-01-04", "home_team": "B", "away_team": "A", "home_score": 0, "away_score": 2},
    ])


def test_features_do_not_use_future_games():
    result = create_features(sample())
    assert result.loc[0, "home_win_rate"] == 0.0
    assert result.loc[2, "home_win_rate"] == 0.5


def test_split_is_chronological():
    train, test = chronological_split(create_features(sample()), 0.5)
    assert train["game_date"].max() < test["game_date"].min()
    assert list(train["game_id"]) == ["1", "2"]


def test_rejects_invalid_fraction():
    with pytest.raises(ValueError):
        chronological_split(create_features(sample()), 1)
