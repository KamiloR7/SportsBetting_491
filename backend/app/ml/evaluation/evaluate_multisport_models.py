"""Evaluate and version Sprint 2 sport baseline models."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, brier_score_loss, log_loss, confusion_matrix

from app.ml.features.engineer_multisport_features import FEATURE_COLUMNS, chronological_split


def evaluate_model(model, data: pd.DataFrame) -> dict:
    """Return classification and probability-quality metrics."""
    train, test = chronological_split(data)
    predictions = model.predict(test[FEATURE_COLUMNS])
    probabilities = model.predict_proba(test[FEATURE_COLUMNS])
    if probabilities.ndim != 2 or probabilities.shape[1] != 2:
        raise ValueError("The model must return two outcome probabilities")
    if not (probabilities >= 0).all() or not (probabilities <= 1).all():
        raise ValueError("Prediction probabilities must be between 0 and 1")
    if not (abs(probabilities.sum(axis=1) - 1) < 1e-6).all():
        raise ValueError("Prediction probabilities must sum to 1")
    if list(model.classes_) != [0, 1]:
        raise ValueError("Expected classifier classes [0, 1]")
    positive = probabilities[:, 1]
    actual = test["outcome"].to_numpy()
    calibration = []
    for lower in np.arange(0.0, 1.0, 0.2):
        upper = min(1.0, float(lower + 0.2))
        mask = (positive >= lower) & ((positive < upper) if upper < 1 else (positive <= upper))
        calibration.append({"lower": float(lower), "upper": upper, "count": int(mask.sum()),
                            "mean_probability": float(positive[mask].mean()) if mask.any() else None,
                            "observed_home_win_rate": float(actual[mask].mean()) if mask.any() else None})
    prevalence = float(train["outcome"].mean())
    return {
        "test_rows": int(len(test)),
        "accuracy": float(accuracy_score(test["outcome"], predictions)),
        "precision": float(precision_score(test["outcome"], predictions, zero_division=0)),
        "recall": float(recall_score(test["outcome"], predictions, zero_division=0)),
        "f1": float(f1_score(test["outcome"], predictions, zero_division=0)),
        "probability_mean_sum": float(probabilities.sum(axis=1).mean()),
        "brier_score": float(brier_score_loss(actual, positive)),
        "log_loss": float(log_loss(actual, probabilities, labels=[0, 1])),
        "confusion_matrix_labels_0_1": confusion_matrix(actual, predictions, labels=[0, 1]).tolist(),
        "calibration_bins": calibration,
        "training_prevalence_baseline": {
            "probability": prevalence,
            "accuracy": float(accuracy_score(actual, np.full(len(actual), int(prevalence >= 0.5)))),
            "brier_score": float(brier_score_loss(actual, np.full(len(actual), prevalence))),
            "log_loss": float(log_loss(actual, np.tile([1 - prevalence, prevalence], (len(actual), 1)), labels=[0, 1])),
        },
    }


def model_version(metadata: dict[str, object], source_revision: str = "working-tree") -> str:
    """Create a stable version from model metadata and source revision."""
    payload = json.dumps({"metadata": metadata, "source_revision": source_revision}, sort_keys=True).encode()
    return "sprint2-model-" + hashlib.sha256(payload).hexdigest()[:12]


def write_evaluation(output_directory: Path, sport: str, metrics: dict, metadata: dict, source_revision: str = "working-tree") -> Path:
    """Write versioned evaluation evidence for a sport model."""
    output_directory.mkdir(parents=True, exist_ok=True)
    version = model_version(metadata, source_revision)
    result = {"sport": sport.upper(), "model_version": version, "source_revision": source_revision, "metrics": metrics}
    path = output_directory / f"{sport.lower()}_evaluation.json"
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return path
