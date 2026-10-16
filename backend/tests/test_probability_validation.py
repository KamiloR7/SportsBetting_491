"""Sprint 3 probability validation tests for NFL, MLB, and EPL."""

import pytest

from app.ml.probability_validation import (
    validate_probabilities,
    validate_sport_probabilities,
)


# -------------------------------------
# Valid binary and three-way probabilities
# -------------------------------------

@pytest.mark.parametrize(
    "sport,probabilities",
    [
        ("NFL", {"home_win": 0.55, "away_win": 0.45}),
        ("MLB", {"home_win": 0.65, "away_win": 0.35}),
        (
            "EPL",
            {"home_win": 0.45, "draw": 0.30, "away_win": 0.25},
        ),
    ],
)
def test_valid_probabilities(sport, probabilities):
    assert validate_probabilities(probabilities)


# -------------------------------------
# Invalid probability values
# -------------------------------------

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


# -------------------------------------
# Valid sport-specific outcomes
# -------------------------------------

@pytest.mark.parametrize(
    "sport,probabilities",
    [
        ("NFL", {"home_win": 0.55, "away_win": 0.45}),
        ("MLB", {"home_win": 0.65, "away_win": 0.35}),
        (
            "EPL",
            {"home_win": 0.45, "draw": 0.30, "away_win": 0.25},
        ),
    ],
)
def test_valid_sport_probabilities(sport, probabilities):
    assert validate_sport_probabilities(sport, probabilities)


# -------------------------------------
# Invalid sport-specific outcomes
# -------------------------------------

@pytest.mark.parametrize(
    "sport,probabilities",
    [
        # NFL must not have a draw class
        ("NFL", {"home_win": 0.60, "draw": 0.40}),

        # MLB must not have a draw class
        ("MLB", {"home_win": 0.70, "draw": 0.30}),

        # EPL requires three outcome classes
        ("EPL", {"home_win": 0.60, "away_win": 0.40}),

        # EPL must reject unexpected classes
        (
            "EPL",
            {"home_win": 0.50, "draw": 0.30, "tie": 0.20},
        ),
    ],
)
def test_invalid_sport_probabilities(sport, probabilities):
    with pytest.raises(ValueError):
        validate_sport_probabilities(sport, probabilities)


# -------------------------------------
# Unsupported sports
# -------------------------------------

@pytest.mark.parametrize("sport", ["NBA", "UEFA", "NHL"])
def test_unsupported_sport_rejected(sport):
    with pytest.raises(ValueError, match="Unsupported sport"):
        validate_sport_probabilities(
            sport,
            {"home_win": 0.60, "away_win": 0.40},
        )