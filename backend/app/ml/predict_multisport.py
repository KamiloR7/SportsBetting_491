"""Prediction interface for trusted, locally produced baseline artifacts."""
from __future__ import annotations

import hashlib
import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from app.ml.features.engineer_multisport_features import FEATURE_COLUMNS


def load_trusted_baseline(path: Path):
    """Never load a pickle or metadata supplied by an untrusted party."""
    metadata = json.loads(path.with_suffix(".json").read_text())
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != metadata["model_sha256"]:
        raise ValueError("Model checksum mismatch")
    return pickle.loads(payload), metadata


def predict_outcomes(model, features: pd.DataFrame) -> pd.DataFrame:
    missing = set(FEATURE_COLUMNS) - set(features.columns)
    if missing:
        raise ValueError(f"Missing prediction features: {sorted(missing)}")
    if features.empty:
        raise ValueError("Prediction input must not be empty")
    values = features[FEATURE_COLUMNS].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Prediction features must be finite and nonnegative")
    if (features[["home_win_rate", "away_win_rate"]].to_numpy(dtype=float) > 1).any():
        raise ValueError("Win rates must be between zero and one")
    if list(model.classes_) != [0, 1]:
        raise ValueError("Expected binary classes [0, 1]")
    probabilities = model.predict_proba(features[FEATURE_COLUMNS])
    if probabilities.shape != (len(features), 2) or not np.isfinite(probabilities).all():
        raise ValueError("Invalid probability shape or values")
    if (probabilities < 0).any() or (probabilities > 1).any() or not np.allclose(probabilities.sum(axis=1), 1):
        raise ValueError("Invalid probability distribution")
    return pd.DataFrame({
        "predicted_outcome": model.predict(features[FEATURE_COLUMNS]),
        "probability_not_home_win": probabilities[:, 0],
        "probability_home_win": probabilities[:, 1],
    }, index=features.index)
