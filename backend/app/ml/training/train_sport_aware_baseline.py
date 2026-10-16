"""Sprint 3 sport-aware binary and three-way baseline training."""

import numpy as np
import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.ml.features.engineer_multisport_features import (
    FEATURE_COLUMNS,
    chronological_split,
)


SPORT_CLASSES = {
    "NFL": {"home_win", "away_win"},
    "MLB": {"home_win", "away_win"},
    "EPL": {"home_win", "draw", "away_win"},
}


def train_sport_aware_baseline(
    data: pd.DataFrame,
    sport: str,
):
    """Train a reproducible sport-specific outcome classifier."""

    sport = sport.upper()

    if sport not in SPORT_CLASSES:
        raise ValueError(f"Unsupported sport: {sport}")

    required = set(FEATURE_COLUMNS + ["game_id", "game_date", "outcome"])
    missing = required - set(data.columns)

    if missing:
        raise ValueError(f"Missing training columns: {sorted(missing)}")

    expected_classes = SPORT_CLASSES[sport]

    if data.empty:
        raise ValueError("Training data must not be empty")

    if not data["outcome"].isin(expected_classes).all():
        raise ValueError(f"Invalid outcome labels for {sport}")

    values = data[FEATURE_COLUMNS].to_numpy(dtype=float)

    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError(
            "Training features must be finite and nonnegative"
        )

    for column in ("home_win_rate", "away_win_rate"):
        if (data[column] > 1).any():
            raise ValueError(
                f"{column} must be between zero and one"
            )

    train, test = chronological_split(data)

    if set(train["outcome"]) != expected_classes:
        raise ValueError(
            f"{sport} training partition must contain "
            f"all required outcome classes"
        )

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(
            max_iter=1000,
            random_state=42,
        )),
    ])

    model.fit(train[FEATURE_COLUMNS], train["outcome"])

    metadata = {
        "sport": sport,
        "model_type": "logistic_regression",
        "feature_columns": list(FEATURE_COLUMNS),
        "classes": list(model.classes_),
        "train_rows": len(train),
        "test_rows": len(test),
        "split": "chronological_whole_dates",
        "random_state": 42,
        "train_start": train["game_date"].min().isoformat(),
        "train_end": train["game_date"].max().isoformat(),
        "test_start": test["game_date"].min().isoformat(),
        "test_end": test["game_date"].max().isoformat(),
        "train_class_counts": {
            str(label): int(count)
            for label, count
            in train["outcome"].value_counts().items()
        },
    }

    return model, metadata