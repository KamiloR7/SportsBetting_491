"""Run the reproducible Sprint 2 training/evaluation pipeline from repository root."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path

import numpy as np

from app.ml.features.prepare_multisport_data import load_all_datasets
from app.ml.features.engineer_multisport_features import create_features, chronological_split, FEATURE_COLUMNS
from app.ml.training.train_multisport_baseline import train_baseline, save_baseline
from app.ml.evaluation.evaluate_multisport_models import evaluate_model, write_evaluation
from app.ml.predict_multisport import load_trusted_baseline, predict_outcomes


def source_identity() -> dict:
    root = Path(__file__).resolve().parent
    files = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
             for path in sorted(root.rglob("*.py"))}
    digest = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "--", "backend/app/ml"], text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        revision, dirty = "unavailable", True
    return {"git_head": revision, "uncommitted_ml_changes": dirty, "ml_source_sha256": digest, "files": files}


def run_pipeline(raw_directory: Path, output_directory: Path) -> dict:
    datasets = load_all_datasets(raw_directory)
    provenance = json.loads((raw_directory / "provenance.json").read_text())
    identity = source_identity()
    reports = {"source": identity, "python_version": platform.python_version(),
               "evaluation_protocol": "Fixed trained model, chronological holdout, expanding prior-day observed results. No same-day results or holdout-based tuning.",
               "target": "Home win versus not-home-win (draw included in not-home-win).",
               "sports": {}}
    for sport, games in datasets.items():
        raw_path = raw_directory / f"{sport.lower()}_games.csv"
        dataset_hash = hashlib.sha256(raw_path.read_bytes()).hexdigest()
        if dataset_hash != provenance["sports"][sport]["dataset_sha256"]:
            raise ValueError(f"{sport} dataset no longer matches provenance")
        features = create_features(games)
        train, test = chronological_split(features)
        model, metadata = train_baseline(features, sport)
        metadata.update({"dataset_sha256": dataset_hash, "source": identity,
                         "python_version": platform.python_version()})
        model_path = save_baseline(model, metadata, output_directory)
        saved_metadata = json.loads(model_path.with_suffix(".json").read_text())
        reloaded, _ = load_trusted_baseline(model_path)
        np.testing.assert_allclose(model.predict_proba(test[FEATURE_COLUMNS]),
                                   reloaded.predict_proba(test[FEATURE_COLUMNS]), rtol=0, atol=0)
        metrics = evaluate_model(reloaded, features)
        artifact_directory = model_path.parent
        evaluation_path = write_evaluation(artifact_directory, sport, metrics, saved_metadata, identity["ml_source_sha256"])
        features.to_csv(artifact_directory / "features.csv", index=False)
        train.to_csv(artifact_directory / "train.csv", index=False)
        test.to_csv(artifact_directory / "test.csv", index=False)
        predictions = test[["game_id", "game_date", "outcome"]].copy()
        prediction_output = predict_outcomes(reloaded, test[FEATURE_COLUMNS])
        for column in prediction_output:
            predictions[column] = prediction_output[column]
        predictions.to_csv(artifact_directory / "predictions.csv", index=False)
        reports["sports"][sport] = {
            "dataset": provenance["sports"][sport], "metadata": saved_metadata, "metrics": metrics,
            "reload_predictions_identical": True, "artifact_directory": str(artifact_directory),
            "evaluation_file": str(evaluation_path),
            "draws_encoded_as_not_home_win": int(games["home_score"].eq(games["away_score"]).sum()),
        }
    (output_directory / "report.json").write_text(json.dumps(reports, indent=2, allow_nan=False) + "\n")
    return reports


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--output", type=Path, default=Path("build/sprint2-models"))
    arguments = parser.parse_args()
    report = run_pipeline(arguments.raw, arguments.output)
    for sport, result in report["sports"].items():
        print(sport, json.dumps(result["metrics"]))
