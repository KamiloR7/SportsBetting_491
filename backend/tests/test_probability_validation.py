import pytest

from app.ml.probability_validation import validate_probabilities


def test_valid_nba_probabilities():
    probabilities = {
        "home_win": 0.65,
        "away_win": 0.35,
    }

    assert validate_probabilities(probabilities)


def test_valid_nfl_probabilities():
    probabilities = {
        "home_win": 0.55,
        "away_win": 0.45,
    }

    assert validate_probabilities(probabilities)


def test_valid_uefa_probabilities():
    probabilities = {
        "home_win": 0.45,
        "draw": 0.30,
        "away_win": 0.25,
    }

    assert validate_probabilities(probabilities)


@pytest.mark.parametrize(
    "probabilities",
    [
        {"home_win": 0.8, "away_win": 0.4},
        {"home_win": -0.2, "away_win": 1.2},
        {"home_win": float("nan"), "away_win": 0.5},
        {"home_win": float("inf"), "away_win": 0.5},
        {"home_win": 1.0},
        {},
    ],
)
def test_invalid_probabilities(probabilities):
    with pytest.raises(ValueError):
        validate_probabilities(probabilities)