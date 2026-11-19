"""Reproduce saved market-model holdouts without replacing models or writing the DB.
Run from backend: python -m app.ml.evaluation.market_audit
"""
import hashlib
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, log_loss

from app.ml.features.engineer_multisport_features import FEATURE_COLUMNS, chronological_split
from app.ml.features.sport_aware_features import create_sport_aware_features
from app.ml.training.train_sport_aware_baseline import train_sport_aware_baseline


def distribution_metrics(actual, probabilities, classes):
    """Top-label calibration: confidence of the chosen outcome versus correctness."""
    actual = np.asarray(actual)
    probabilities = np.asarray(probabilities, dtype=float)
    if probabilities.shape != (len(actual), len(classes)) or not len(actual):
        raise ValueError("Invalid evaluation dimensions")
    if (not np.isfinite(probabilities).all() or (probabilities < 0).any()
            or (probabilities > 1).any() or not np.allclose(probabilities.sum(axis=1), 1)):
        raise ValueError("Invalid evaluation probabilities")
    if not set(actual).issubset(set(classes)):
        raise ValueError("Unknown actual outcome")
    predicted = np.asarray(classes)[probabilities.argmax(axis=1)]
    correct = predicted == actual
    confidence = probabilities.max(axis=1)
    bin_indices = np.minimum((confidence * 10).astype(int), 9)
    bins = []
    for index in range(10):
        selected = bin_indices == index
        count = int(selected.sum())
        bins.append({"lower": index / 10, "upper": (index + 1) / 10, "count": count,
                     "mean_confidence": float(confidence[selected].mean()) if count else None,
                     "accuracy": float(correct[selected].mean()) if count else None})
    return {"accuracy": float(correct.mean()),
            "correct": int(correct.sum()),
            "log_loss": float(log_loss(actual, probabilities, labels=classes)),
            "confusion_matrix": confusion_matrix(actual, predicted, labels=classes).tolist(),
            "calibration_bins": bins,
            "expected_calibration_error": float(sum(b["count"] / len(actual) * abs(b["mean_confidence"] - b["accuracy"]) for b in bins if b["count"]))}


def evaluate_sport(games, sport, deployed_metadata, manifest_item, cutoff):
    games = games.loc[pd.to_datetime(games.game_date, utc=True).dt.normalize() < cutoff]
    frame = create_sport_aware_features(games, sport)
    dataset_hash = hashlib.sha256(frame.to_csv(index=False).encode()).hexdigest()
    if dataset_hash != deployed_metadata.get("dataset_sha256"):
        raise ValueError("Stored results differ from this model's training snapshot; its holdout cannot be reproduced exactly.")
    train, test = chronological_split(frame)
    model, metadata = train_sport_aware_baseline(frame, sport)
    metrics = distribution_metrics(test.outcome, model.predict_proba(test[FEATURE_COLUMNS]), list(model.classes_))
    saved = manifest_item["metrics"]
    if len(test) != saved["test_rows"] or len(train) != saved["train_rows"] or not np.isclose(metrics["accuracy"], saved["accuracy"], atol=1e-12, rtol=0) or not np.isclose(metrics["log_loss"], saved["log_loss"], atol=1e-10, rtol=0):
        raise ValueError("Reproduced holdout does not match saved accuracy; verify the training environment.")
    baseline = str(train.outcome.mode().iloc[0])
    return {"sport": sport, "model_version": deployed_metadata["artifact_version"],
            "model_type": "StandardScaler + LogisticRegression", "classes": list(model.classes_),
            "dataset_sha256": dataset_hash, "snapshot_verified": True,
            "train_rows": len(train), "test_rows": len(test),
            "train_start": metadata["train_start"], "train_end": metadata["train_end"],
            "test_start": metadata["test_start"], "test_end": metadata["test_end"],
            "baseline_outcome": baseline,
            "baseline_accuracy": float((test.outcome == baseline).mean()), **metrics}


def main():
    from app.core.config import settings
    from app.database.db import engine
    from app.ml.train_local_match_models import completed_games
    from app.services.model_odds import MarketModelRegistry
    directory = settings.MARKET_MODEL_DIRECTORY
    manifest_bytes = (directory / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    cutoff = pd.Timestamp(manifest["generated_at"]).tz_convert("UTC").normalize()
    report = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
              "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
              "source_generated_at": manifest["generated_at"], "data_cutoff": cutoff.isoformat(),
              "method": "chronological_whole_dates_train_only_scaler", "sports": [], "unavailable": []}
    registry = MarketModelRegistry(directory)
    with engine.connect() as conn:
        for sport in ("NFL", "MLB", "EPL"):
            try:
                _, metadata = registry.get(sport)
                item = evaluate_sport(completed_games(conn, sport), sport, metadata, manifest["sports"][sport], cutoff)
                report["sports"].append(item)
                print(f"{sport}: {item['correct']}/{item['test_rows']} correct; snapshot verified", flush=True)
            except (ValueError, KeyError, OSError) as exc:
                report["unavailable"].append({"sport": sport, "reason": str(exc) if isinstance(exc, ValueError) else "Local evaluation artifact is missing or incompatible."})
                print(f"{sport}: unavailable: {exc}", flush=True)
    temporary = directory / "evaluation.next.json"
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(directory / "evaluation.json")


if __name__ == "__main__":
    main()
