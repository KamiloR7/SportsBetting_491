"""Chronological, sport-specific evaluation without refitting on held-out labels."""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support

from app.ml.features.historical_sport_features import build_sport_feature_dataset
from app.ml.historical_baselines import (
    METHODS, BaselinePredictor, InsufficientHistoryError, outcome_classes,
)


def _metrics(actual, predictions, classes):
    if not actual:
        return None
    precision, recall, f1, support = precision_recall_fscore_support(
        actual, predictions, labels=list(classes), zero_division=0,
    )
    return {
        "accuracy": float(accuracy_score(actual, predictions)),
        "precision": float(precision.mean()), "recall": float(recall.mean()),
        "f1": float(f1.mean()), "average": "macro", "class_order": list(classes),
        "confusion_matrix": confusion_matrix(actual, predictions, labels=list(classes)).tolist(),
        "per_class": {label: {"precision": float(precision[index]),
                              "recall": float(recall[index]), "f1": float(f1[index]),
                              "support": int(support[index])}
                      for index, label in enumerate(classes)},
    }


def evaluate_baselines(
    records: Iterable[Mapping[str, Any]], sport: str, test_fraction: float = 0.2,
    *, min_training_matches=1, min_team_matches=1,
) -> dict:
    """Return one sport report; callers must supply genuine data for real metrics.

    Missing form history is counted explicitly. Malformed data aborts evaluation
    rather than being disguised as missing history. Common-cohort metrics support
    fair comparisons when the form baseline cannot predict every held-out match.
    """
    dataset = build_sport_feature_dataset(records, sport, test_fraction)
    baseline = BaselinePredictor.fit(
        dataset, min_training_matches=min_training_matches, min_team_matches=min_team_matches,
    )
    classes = outcome_classes(dataset.sport)
    labeled = dataset.test[dataset.test["outcome"].notna()]
    actual_by_id = dict(zip(labeled["game_id"], labeled["outcome"]))
    methods = {}
    for method in METHODS:
        predictions, skipped = [], []
        for index in labeled.index:
            match = labeled.loc[[index]]
            try:
                predictions.extend(baseline.predict(match, method, schema_version=dataset.schema_version))
            except InsufficientHistoryError as exc:
                skipped.append({"match_id": match.iloc[0]["game_id"], "reason": str(exc)})
        actual = [actual_by_id[row["match_id"]] for row in predictions]
        methods[method] = {
            "evaluated_rows": len(predictions), "skipped_insufficient_history": skipped,
            "coverage": len(predictions) / len(labeled) if len(labeled) else None,
            "metrics": _metrics(actual, [row["predicted_outcome"] for row in predictions], classes),
            "predictions": predictions,
        }
    common = set.intersection(*(set(row["match_id"] for row in report["predictions"])
                                for report in methods.values()))
    common_ids = [match_id for match_id in labeled["game_id"] if match_id in common]
    for report in methods.values():
        predictions_by_id = {row["match_id"]: row["predicted_outcome"] for row in report["predictions"]}
        report["common_cohort_metrics"] = _metrics(
            [actual_by_id[match_id] for match_id in common_ids],
            [predictions_by_id[match_id] for match_id in common_ids], classes,
        )
    return {
        "sport": dataset.sport, "schema_version": dataset.schema_version,
        "train_rows": len(dataset.train), "test_rows": len(dataset.test),
        "labeled_training_rows": sum(baseline.class_counts),
        "excluded_training_ties": baseline.excluded_training_ties,
        "excluded_test_ties": int(dataset.test["outcome"].isna().sum()),
        "labeled_test_rows": len(labeled),
        "train_end_day": baseline.training_end_day.isoformat(),
        "training_labels_available_at": baseline.labels_available_at.isoformat(),
        "test_start_day": dataset.test["game_date"].min().isoformat(),
        "frequency_probabilities": baseline.probabilities,
        "evaluation_policy": "frozen_training_frequencies_with_rolling_available_test_features",
        "common_cohort_match_ids": common_ids, "methods": methods,
    }
