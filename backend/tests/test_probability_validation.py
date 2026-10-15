import pytest

from app.ml.probability_validation import (
    validate_probabilities,
    validate_sport_probabilities,
)

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

# =====================================
# Sprint 3 - S3-04.02
# Sport-specific probability validation
# =====================================

@pytest.mark.parametrize(
    "sport, probabilities",
    [
        (
            "NBA",
            {"home_win": 0.65, "away_win": 0.35},
        ),
        (
            "NFL",
            {"home_win": 0.55, "away_win": 0.45},
        ),
        (
            "UEFA",
            {
                "home_win": 0.45,
                "draw": 0.30,
                "away_win": 0.25,
            },
        ),
    ],
)
def test_valid_sport_probabilities(sport, probabilities):
    assert validate_sport_probabilities(sport, probabilities)


@pytest.mark.parametrize(
    "sport, probabilities",
    [
        # NBA must not have a draw outcome
        (
            "NBA",
            {"home_win": 0.60, "draw": 0.40},
        ),

        # NFL must have home_win and away_win
        (
            "NFL",
            {"home_win": 0.70, "draw": 0.30},
        ),

        # UEFA requires three outcome classes
        (
            "UEFA",
            {"home_win": 0.60, "away_win": 0.40},
        ),

        # UEFA must reject unexpected classes
        (
            "UEFA",
            {
                "home_win": 0.50,
                "draw": 0.30,
                "tie": 0.20,
            },
        ),
    ],
)
def test_invalid_sport_probabilities(sport, probabilities):
    with pytest.raises(ValueError):
        validate_sport_probabilities(sport, probabilities)