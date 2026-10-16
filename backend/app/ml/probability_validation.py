import math


# Expected prediction classes for each sport
EXPECTED_CLASSES = {
    "NFL": {"home_win", "away_win"},
    "MLB": {"home_win", "away_win"},
    "EPL": {"home_win", "draw", "away_win"},
}


def validate_probabilities(probabilities):
    """
    Validate model prediction probabilities.

    Supports both binary and three-way match predictions.
    """

    if not isinstance(probabilities, dict):
        raise ValueError("Probabilities must be a dictionary")

    if len(probabilities) not in (2, 3):
        raise ValueError("Expected 2 or 3 outcome probabilities")

    for outcome, probability in probabilities.items():

        if not isinstance(outcome, str) or not outcome:
            raise ValueError("Invalid outcome label")

        if type(probability) not in (int, float):
            raise ValueError("Probability must be numeric")

        if not math.isfinite(probability):
            raise ValueError("Probability must be finite")

        if not 0 <= probability <= 1:
            raise ValueError(
                "Probability must be between 0 and 1"
            )

    # Check that probabilities total 100%
    if not math.isclose(
        sum(probabilities.values()),
        1.0,
        rel_tol=0.0,
        abs_tol=1e-6,
    ):
        raise ValueError("Probabilities must sum to 1")

    return True


def validate_sport_probabilities(sport, probabilities):
    """
    Validate the expected outcome classes for each sport.
    """

    if not isinstance(sport, str):
        raise ValueError("Sport must be a string")

    sport = sport.upper()

    if sport not in EXPECTED_CLASSES:
        raise ValueError(f"Unsupported sport: {sport}")

    # First validate probability values
    validate_probabilities(probabilities)

    # Check sport-specific classes
    expected = EXPECTED_CLASSES[sport]
    actual = set(probabilities.keys())

    if actual != expected:
        raise ValueError(
            f"Invalid outcome classes for {sport}. "
            f"Expected {sorted(expected)}, "
            f"got {sorted(actual)}"
        )

    return True