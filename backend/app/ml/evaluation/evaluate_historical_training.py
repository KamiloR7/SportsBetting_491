"""Chronological comparison of a trained sport model and both historical baselines."""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from app.ml.evaluation.evaluate_historical_baselines import _metrics as classification_metrics
from app.ml.features.historical_sport_features import build_sport_feature_dataset
from app.ml.historical_baselines import BaselinePredictor, InsufficientHistoryError, METHODS, outcome_classes
from app.ml.training.historical_match_model import train_historical_model


def train_and_evaluate_sport(
    records: Iterable[Mapping[str, Any]], sport: str, test_fraction: float = 0.2,
    *, min_samples_per_class: int = 2, min_team_matches: int = 1,
):
    """Return (model, report) for one sport; genuine inputs are required for real metrics.

    Train once, retain the original held-out partition, and compare all methods on
    their shared eligible cohort. Only explicit baseline cold starts are skipped.
    """
    dataset = build_sport_feature_dataset(records, sport, test_fraction)
    model = train_historical_model(dataset, min_samples_per_class=min_samples_per_class)
    baseline = BaselinePredictor.fit(dataset, min_team_matches=min_team_matches)
    predictors = {"logistic_regression": lambda frame: model.predict(frame, schema_version=dataset.schema_version)}
    for method in METHODS:
        predictors[method] = lambda frame, selected=method: baseline.predict(
            frame, selected, schema_version=dataset.schema_version,
        )
    labeled = dataset.test[dataset.test["outcome"].notna()]
    actual = dict(zip(labeled["game_id"], labeled["outcome"]))
    classes = outcome_classes(dataset.sport)
    methods = {}
    for method, predict in predictors.items():
        predictions, skipped = [], []
        for index in labeled.index:
            frame = labeled.loc[[index]]
            try:
                predictions.extend(predict(frame))
            except InsufficientHistoryError as exc:
                skipped.append({"match_id": frame.iloc[0]["game_id"], "reason": str(exc)})
        methods[method] = {
            "evaluated_rows": len(predictions),
            "coverage": len(predictions) / len(labeled) if len(labeled) else None,
            "skipped_insufficient_history": skipped,
            "metrics": classification_metrics(
                [actual[row["match_id"]] for row in predictions],
                [row["predicted_outcome"] for row in predictions], classes,
            ),
            "predictions": predictions,
        }
    common = set.intersection(*(set(row["match_id"] for row in method["predictions"])
                                for method in methods.values()))
    common_ids = [match_id for match_id in labeled["game_id"] if match_id in common]
    for method in methods.values():
        predicted = {row["match_id"]: row["predicted_outcome"] for row in method["predictions"]}
        method["common_cohort_metrics"] = classification_metrics(
            [actual[match_id] for match_id in common_ids],
            [predicted[match_id] for match_id in common_ids], classes,
        )
    return model, {
        "sport": dataset.sport, "model_version": model.metadata["model_version"],
        "schema_version": dataset.schema_version, "class_order": list(classes),
        "train_rows": len(dataset.train), "fit_rows": model.metadata["fit_rows"],
        "test_rows": len(dataset.test), "labeled_test_rows": len(labeled),
        "excluded_training_ties": model.metadata["excluded_training_ties"],
        "excluded_test_ties": int(dataset.test["outcome"].isna().sum()),
        "train_end_day": model.metadata["training_end_day"],
        "training_labels_available_at": model.metadata["training_labels_available_at"],
        "test_start_day": dataset.test["game_date"].min().isoformat(),
        "evaluation_policy": "train_only_fit_with_rolling_available_test_features",
        "common_cohort_match_ids": common_ids, "methods": methods,
    }
