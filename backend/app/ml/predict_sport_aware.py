"""Sprint 3 sport-aware outcome probability inference."""

import numpy as np
import pandas as pd

from app.ml.features.engineer_multisport_features import FEATURE_COLUMNS
from app.ml.training.train_sport_aware_baseline import SPORT_CLASSES
from backend.app.ml.evaluation.evaluate_multisport_models import model_version


def predict_sport_aware(model, features: pd.DataFrame, sport: str, model_version: str | None = None):
    """Return labeled outcome probabilities for each match."""

    sport = sport.upper()

    if sport not in SPORT_CLASSES:
        raise ValueError(f"Unsupported sport: {sport}")

    required = set(FEATURE_COLUMNS + ["game_id"])
    missing = required - set(features.columns)

    if missing:
        raise ValueError(f"Missing prediction columns: {sorted(missing)}")

    if features.empty:
        raise ValueError("Prediction input must not be empty")

    values = features[FEATURE_COLUMNS].to_numpy(dtype=float)

    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Features must be finite and nonnegative")

    for column in ("home_win_rate", "away_win_rate"):
        if (features[column] > 1).any():
            raise ValueError(f"{column} must be between zero and one")

    classes = list(model.classes_)

    if set(classes) != SPORT_CLASSES[sport]:
        raise ValueError(f"Unexpected model classes for {sport}")

    probabilities = model.predict_proba(features[FEATURE_COLUMNS])

    if probabilities.shape != (len(features), len(classes)):
        raise ValueError("Invalid prediction probability shape")

    if (
        not np.isfinite(probabilities).all()
        or (probabilities < 0).any()
        or (probabilities > 1).any()
        or not np.allclose(probabilities.sum(axis=1), 1)
    ):
        raise ValueError("Invalid probability distribution")

    results = []

    for index, (_, match) in enumerate(features.iterrows()):
        scores = {
            outcome: float(probabilities[index, column])
            for column, outcome in enumerate(classes)
        }

        predicted_outcome = classes[int(np.argmax(probabilities[index]))]

        prediction = {
            "match_id": str(match["game_id"]),
            "sport": sport,
            "predicted_outcome": predicted_outcome,
            "probabilities": scores,
       }

        if model_version is not None:
            if not isinstance(model_version, str) or not model_version.strip():
                raise ValueError("model_version must be a non-empty string")
            prediction["model_version"] = model_version

        results.append(prediction)

    return results