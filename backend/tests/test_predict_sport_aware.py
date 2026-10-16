"""Tests for Sprint 3 sport-aware probability inference."""

import numpy as np
import pandas as pd
import pytest

from app.ml.features.engineer_multisport_features import FEATURE_COLUMNS
from app.ml.predict_sport_aware import predict_sport_aware


class MockModel:
    def __init__(self, classes, probabilities):
        self.classes_ = np.array(classes)
        self.probabilities = np.array(probabilities)

    def predict_proba(self, features):
        return np.tile(self.probabilities, (len(features), 1))


@pytest.fixture
def sample_features():
    row = {column: 0.5 for column in FEATURE_COLUMNS}
    row["game_id"] = "test-match-001"
    return pd.DataFrame([row])


@pytest.mark.parametrize("sport", ["NFL", "MLB"])
def test_binary_probabilities(sport, sample_features):
    model = MockModel(
        ["away_win", "home_win"],
        [0.35, 0.65],
    )

    result = predict_sport_aware(model, sample_features, sport)

    assert len(result) == 1
    assert result[0]["match_id"] == "test-match-001"
    assert result[0]["sport"] == sport
    assert result[0]["predicted_outcome"] == "home_win"
    assert result[0]["probabilities"]["home_win"] == pytest.approx(0.65)
    assert sum(result[0]["probabilities"].values()) == pytest.approx(1.0)


def test_epl_three_way_probabilities(sample_features):
    model = MockModel(
        ["away_win", "draw", "home_win"],
        [0.50, 0.30, 0.20],
    )

    result = predict_sport_aware(model, sample_features, "EPL")

    assert result[0]["predicted_outcome"] == "away_win"
    assert set(result[0]["probabilities"]) == {
        "home_win", "draw", "away_win"
    }
    assert result[0]["probabilities"]["draw"] == pytest.approx(0.30)
    assert sum(result[0]["probabilities"].values()) == pytest.approx(1.0)


def test_incorrect_model_classes_rejected(sample_features):
    model = MockModel(
        ["away_win", "home_win"],
        [0.4, 0.6],
    )

    with pytest.raises(ValueError, match="Unexpected model classes"):
        predict_sport_aware(model, sample_features, "EPL")


def test_invalid_probabilities_rejected(sample_features):
    model = MockModel(
        ["away_win", "home_win"],
        [0.8, 0.8],
    )

    with pytest.raises(ValueError, match="Invalid probability distribution"):
        predict_sport_aware(model, sample_features, "NFL")


def test_negative_features_rejected(sample_features):
    sample_features.loc[0, "home_win_rate"] = -0.2

    model = MockModel(
        ["away_win", "home_win"],
        [0.4, 0.6],
    )

    with pytest.raises(ValueError, match="nonnegative"):
        predict_sport_aware(model, sample_features, "NFL")

def test_model_version_in_prediction(sample_features):
    model = MockModel(
        ["away_win", "home_win"],
        [0.35, 0.65],
    )

    result = predict_sport_aware(
        model,
        sample_features,
        "NFL",
        model_version="05998ba2af32c6a16a38",
    )

    assert result[0]["model_version"] == "05998ba2af32c6a16a38"
    assert result[0]["predicted_outcome"] == "home_win"


def test_invalid_model_version_rejected(sample_features):
    model = MockModel(
        ["away_win", "home_win"],
        [0.35, 0.65],
    )

    with pytest.raises(ValueError, match="model_version"):
        predict_sport_aware(
            model,
            sample_features,
            "NFL",
            model_version="",
        )