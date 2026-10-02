"""Evaluate and version Sprint 2 sport baseline models."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

from app.ml.features.engineer_multisport_features import FEATURE_COLUMNS, chronological_split


def evaluate_model(model, data: pd.DataFrame) -> dict[str, float | int]:
    """Return classification and probability-quality metrics."""
    _, test = chronological_split(data)
    predictions = model.predict(test[FEATURE_COLUMNS])
    probabilities = model.predict_proba(test[FEATURE_COLUMNS])
    if probabilities.ndim != 2 or probabilities.shape[1] != 2:
        raise ValueError("The model must return two outcome probabilities")
    if not (probabilities >= 0).all() or not (probabilities <= 1).all():
        raise ValueError("Prediction probabilities must be between 0 and 1")
    if not (abs(probabilities.sum(axis=1) - 1) < 1e-6).all():
        raise ValueError("Prediction probabilities must sum to 1")
    return {
        "test_rows": int(len(test)),
        "accuracy": float(accuracy_score(test["outcome"], predictions)),
        "precision": float(precision_score(test["outcome"], predictions, zero_division=0)),
        "recall": float(recall_score(test["outcome"], predictions, zero_division=0)),
        "f1": float(f1_score(test["outcome"], predictions, zero_division=0)),
        "probability_mean_sum": float(probabilities.sum(axis=1).mean()),
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
