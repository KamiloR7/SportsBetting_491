"""Offline Sprint 3 sport-aware training smoke test.

Uses synthetic matches only. No external datasets or APIs required.
"""

import json
from pathlib import Path

import pandas as pd
import numpy as np

from app.ml.features.sport_aware_features import (
    create_sport_aware_features,
)
from app.ml.features.engineer_multisport_features import (
    chronological_split,
)
from app.ml.training.train_sport_aware_baseline import (
    train_sport_aware_baseline,
)
from app.ml.training.train_multisport_baseline import save_baseline
from app.ml.predict_multisport import load_trusted_baseline
from app.ml.predict_sport_aware import predict_sport_aware
from app.ml.probability_validation import validate_sport_probabilities


def make_synthetic_games(sport):
    """Create deterministic completed matches across 36 dates."""

    rows = []

    outcomes = (
        ["home_win", "draw", "away_win"]
        if sport == "EPL"
        else ["home_win", "away_win"]
    )

    for index in range(36):
        outcome = outcomes[index % len(outcomes)]

        if outcome == "home_win":
            home_score, away_score = 3, 1
        elif outcome == "away_win":
            home_score, away_score = 1, 3
        else:
            home_score, away_score = 2, 2

        rows.append({
            "game_id": f"{sport}-SMOKE-{index:03d}",
            "game_date": (
                pd.Timestamp("2025-01-01")
                + pd.Timedelta(days=index)
            ).isoformat(),
            "home_team": "Synthetic Home",
            "away_team": "Synthetic Away",
            "home_score": home_score,
            "away_score": away_score,
        })

    return pd.DataFrame(rows)


def run_smoke_test(output_directory):
    """Train, reload, and verify all required sport models."""

    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    report = {
        "test_type": "synthetic_offline_training_smoke",
        "sports": {},
    }

    for sport in ("NFL", "MLB", "EPL"):
        games = make_synthetic_games(sport)
        features = create_sport_aware_features(games, sport)

        model, metadata = train_sport_aware_baseline(
            features, sport
        )

        model_path = save_baseline(
            model,
            metadata,
            output_directory / "models",
        )

        loaded_model, saved_metadata = load_trusted_baseline(
            model_path
        )

        _, test = chronological_split(features)

        predictions = predict_sport_aware(
            loaded_model,
            test,
            sport,
            model_version=saved_metadata["artifact_version"],
        )

        expected_classes = (
            {"home_win", "draw", "away_win"}
            if sport == "EPL"
            else {"home_win", "away_win"}
        )

        assert set(loaded_model.classes_) == expected_classes
        assert len(predictions) == len(test)

        for prediction in predictions:
            validate_sport_probabilities(
                sport,
                prediction["probabilities"],
            )
            assert prediction["predicted_outcome"] in expected_classes
            assert prediction["model_version"] == saved_metadata[
                "artifact_version"
            ]

        report["sports"][sport] = {
            "status": "passed",
            "training_rows": metadata["train_rows"],
            "test_rows": metadata["test_rows"],
            "classes": list(loaded_model.classes_),
            "model_version": saved_metadata["artifact_version"],
            "predictions_validated": len(predictions),
            "sample_prediction": predictions[0],
        }

        print(f"{sport}: PASSED")

    report_path = output_directory / "report.json"
    report_path.write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n"
    )

    print(f"Smoke-test report: {report_path}")
    return report


if __name__ == "__main__":
    run_smoke_test(Path("build/sprint3-ml-smoke"))