import math


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
            raise ValueError("Probability must be between 0 and 1")

    if not math.isclose(
        sum(probabilities.values()), 1.0, abs_tol=1e-6
    ):
        raise ValueError("Probabilities must sum to 1")

    return True