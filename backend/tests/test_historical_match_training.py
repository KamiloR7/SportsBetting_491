"""Synthetic engineering verification only; no real-data performance claims."""
from copy import deepcopy
import json
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from app.ml.evaluation.evaluate_historical_training import train_and_evaluate_sport
from app.ml.features.historical_sport_features import SCHEMA_VERSION, build_sport_feature_dataset
from app.ml.historical_baselines import InsufficientHistoryError, METHODS, outcome_classes
from app.ml.training.historical_match_model import (
    load_historical_model, save_historical_model, train_historical_model,
)
from backend.tests.test_historical_sport_features import match


def records(sport="NFL", length=30):
    rows = []
    for day in range(1, length + 1):
        result = day % 3
        home, away = (3, 1) if result == 1 else (1, 3) if result == 2 else (2, 2)
        if sport == "MLB" and result == 0:
            home, away = 4, 1
        rows.append(match(day, home_score=home, away_score=away, sport=sport))
    return rows


def dataset(sport="NFL"):
    return build_sport_feature_dataset(records(sport), sport)


@pytest.mark.parametrize("sport", ["NFL", "MLB", "EPL"])
def test_train_predict_class_order_probability_contract_and_ties(sport):
    data = dataset(sport)
    original_train, original_test = data.train.copy(deep=True), data.test.copy(deep=True)
    model = train_historical_model(data)
    result = model.predict(data.test, schema_version=SCHEMA_VERSION)
    assert len(result) == len(data.test)
    assert model.metadata["class_order"] == list(outcome_classes(sport))
    assert model.metadata["fit_rows"] == data.train["outcome"].notna().sum()
    assert model.metadata["excluded_training_ties"] == (8 if sport == "NFL" else 0)
    for prediction in result:
        assert list(prediction["probabilities"]) == list(outcome_classes(sport))
        assert prediction["class_order"] == list(outcome_classes(sport))
        assert prediction["feature_schema_version"] == SCHEMA_VERSION
        assert prediction["sport"] == sport
        assert prediction["model_version"] == model.metadata["model_version"]
        assert all(np.isfinite(value) and 0 <= value <= 1 for value in prediction["probabilities"].values())
        assert abs(sum(prediction["probabilities"].values()) - 1) <= 1e-6
    pd.testing.assert_frame_equal(data.train, original_train)
    pd.testing.assert_frame_equal(data.test, original_test)


def test_deterministic_training_from_reordered_inputs():
    data = dataset("EPL")
    model = train_historical_model(data)
    other = train_historical_model(build_sport_feature_dataset(records("EPL")[::-1], "EPL"))
    assert model.metadata == other.metadata
    np.testing.assert_allclose(model.pipeline.named_steps["classifier"].coef_, other.pipeline.named_steps["classifier"].coef_, rtol=0, atol=0)
    assert model.predict(data.test, schema_version=SCHEMA_VERSION) == other.predict(data.test, schema_version=SCHEMA_VERSION)


def test_preprocessing_uses_only_labeled_train_values_not_test_or_ties():
    data = dataset()
    name = "home_recent5_avg_scored"
    data.train[name] = np.nan
    labeled = data.train["outcome"].notna()
    data.train.loc[labeled, name] = 10.0
    data.train.loc[~labeled, name] = 1e6
    data.test[name] = 1e9
    original = data.test.copy(deep=True)
    model = train_historical_model(data)
    index = data.feature_columns.index(name)
    assert model.pipeline.named_steps["imputer"].statistics_[index] == 10
    assert model.pipeline.named_steps["scaler"].mean_[index] == 10
    assert model.pipeline.named_steps["scaler"].n_samples_seen_ == int(labeled.sum())
    assert model.predict(data.test, schema_version=SCHEMA_VERSION)
    pd.testing.assert_frame_equal(data.test, original)


def test_all_missing_train_features_keep_dimensions_without_test_fit():
    data = dataset()
    # A and B only face one another; external opponent strength is all missing.
    name = "home_opponent_win_rate"
    assert data.train[name].isna().all()
    model = train_historical_model(data)
    index = data.feature_columns.index(name)
    assert model.pipeline.named_steps["imputer"].statistics_[index] == 0
    assert name in model.pipeline.feature_names_in_
    assert model.predict(data.test, schema_version=SCHEMA_VERSION)


def test_test_values_and_labels_do_not_affect_model_or_preprocessing():
    data = dataset()
    first = train_historical_model(data)
    data.test[data.feature_columns] = 9999
    data.test["outcome"] = "not-a-label"
    second = train_historical_model(data)
    assert first.metadata == second.metadata
    np.testing.assert_array_equal(first.pipeline.named_steps["classifier"].coef_, second.pipeline.named_steps["classifier"].coef_)
    np.testing.assert_array_equal(first.pipeline.named_steps["imputer"].statistics_, second.pipeline.named_steps["imputer"].statistics_)


@pytest.mark.parametrize("sport", ["NFL", "MLB", "EPL"])
def test_missing_classes_and_insufficient_samples_are_explicit(sport):
    data = dataset(sport)
    data.train["outcome"] = "home_win"
    with pytest.raises(InsufficientHistoryError, match="every supported outcome"):
        train_historical_model(data)
    with pytest.raises(InsufficientHistoryError):
        train_historical_model(dataset(sport), min_samples_per_class=100)


@pytest.mark.parametrize("minimum", [0, -1, True, 1.5])
def test_invalid_minimum(minimum):
    with pytest.raises(ValueError):
        train_historical_model(dataset(), min_samples_per_class=minimum)


@pytest.mark.parametrize("field,value", [
    ("home_recent5_avg_scored", np.inf), ("home_recent5_avg_scored", -1),
    ("home_recent5_avg_scored", "3"), ("home_recent5_avg_scored", True),
    ("home_recent5_avg_margin", complex(1, 2)),
    ("home_season_matches", np.nan), ("home_season_matches", 2.5),
    ("home_season_win_rate", 1.1), ("home_season_points_per_match", 3.5),
])
def test_invalid_predictor_values_fail_before_classifier_execution(field, value):
    data = dataset("EPL")
    model = train_historical_model(data)
    data.test[field] = value
    with patch.object(model.pipeline, "predict_proba", side_effect=AssertionError("must not execute")):
        with pytest.raises(ValueError):
            model.predict(data.test, schema_version=SCHEMA_VERSION)


def test_schema_missing_features_and_training_cutoff_errors():
    data = dataset()
    model = train_historical_model(data)
    with pytest.raises(ValueError, match="schema"):
        model.predict(data.test, schema_version="wrong")
    with pytest.raises(ValueError, match="Missing model feature"):
        model.predict(data.test.drop(columns=data.feature_columns[0]), schema_version=SCHEMA_VERSION)
    with pytest.raises(ValueError, match="training UTC days"):
        model.predict(data.train, schema_version=SCHEMA_VERSION)
    data.test["feature_as_of"] = data.train.iloc[0]["feature_as_of"]
    with pytest.raises(ValueError, match="unavailable"):
        model.predict(data.test, schema_version=SCHEMA_VERSION)


def test_training_schema_order_and_version_are_checked():
    data = dataset()
    data.feature_columns = data.feature_columns[::-1]
    with pytest.raises(ValueError, match="schema"):
        train_historical_model(data)
    data = dataset()
    data.schema_version = "old-version"
    with pytest.raises(ValueError, match="schema"):
        train_historical_model(data)


def test_bad_model_probabilities_rejected():
    data = dataset()
    model = train_historical_model(data)
    for values in [np.full((len(data.test), 2), np.nan), np.ones((len(data.test), 2)), np.zeros((len(data.test), 1))]:
        with patch.object(model.pipeline, "predict_proba", return_value=values):
            with pytest.raises(ValueError):
                model.predict(data.test, schema_version=SCHEMA_VERSION)


@pytest.mark.parametrize("sport", ["NFL", "MLB", "EPL"])
def test_artifact_roundtrip_immutability_and_trust_gate(tmp_path, sport):
    data = dataset(sport)
    model = train_historical_model(data)
    path = save_historical_model(model, tmp_path)
    assert save_historical_model(model, tmp_path) == path
    with pytest.raises(ValueError, match="untrusted"):
        load_historical_model(path)
    loaded = load_historical_model(path, trusted_local=True)
    assert loaded.predict(data.test, schema_version=SCHEMA_VERSION) == model.predict(data.test, schema_version=SCHEMA_VERSION)
    assert loaded.metadata["model_sha256"]
    assert loaded.metadata["artifact_version"]
    original_bytes = path.read_bytes()
    resaved = save_historical_model(loaded, tmp_path)
    assert path.read_bytes() == original_bytes
    assert load_historical_model(resaved, trusted_local=True).predict(data.test, schema_version=SCHEMA_VERSION) == model.predict(data.test, schema_version=SCHEMA_VERSION)


def test_checksum_rejection_before_deserialization(tmp_path):
    path = save_historical_model(train_historical_model(dataset()), tmp_path)
    path.write_bytes(b"corrupt model payload")
    with patch("app.ml.training.historical_match_model.pickle.loads", side_effect=AssertionError("must not deserialize")):
        with pytest.raises(ValueError, match="checksum"):
            load_historical_model(path, trusted_local=True)


@pytest.mark.parametrize("field,value", [
    ("schema_version", "v0"), ("feature_columns", []), ("class_order", ["home_win"]),
    ("versions", {}), ("classifier_config", {}), ("model_version", "wrong"),
])
def test_compatibility_rejection_before_deserialization(tmp_path, field, value):
    path = save_historical_model(train_historical_model(dataset()), tmp_path)
    metadata_path = path.with_suffix(".json")
    metadata = json.loads(metadata_path.read_text())
    metadata[field] = value
    metadata_path.write_text(json.dumps(metadata))
    with patch("app.ml.training.historical_match_model.pickle.loads", side_effect=AssertionError("must not deserialize")):
        with pytest.raises(ValueError):
            load_historical_model(path, trusted_local=True)


@pytest.mark.parametrize("sport", ["NFL", "MLB", "EPL"])
def test_chronological_evaluation_and_baseline_comparison(sport):
    raw = records(sport)
    original = deepcopy(raw)
    model, report = train_and_evaluate_sport(raw, sport)
    assert report["train_rows"] == 24 and report["test_rows"] == 6
    assert report["train_end_day"] < report["test_start_day"]
    assert set(report["methods"]) == {"logistic_regression", *METHODS}
    assert report["class_order"] == list(outcome_classes(sport))
    assert report["excluded_test_ties"] == (2 if sport == "NFL" else 0)
    for method in report["methods"].values():
        assert method["coverage"] == 1
        assert method["common_cohort_metrics"] is not None
        metrics = method["metrics"]
        assert metrics["average"] == "macro"
        assert len(metrics["confusion_matrix"]) == len(outcome_classes(sport))
        assert all(0 <= metrics[name] <= 1 for name in ("accuracy", "precision", "recall", "f1"))
    assert report["model_version"] == model.metadata["model_version"]
    assert raw == original


def test_cold_start_coverage_and_shared_comparison_cohort():
    raw = records()
    for row in raw[24:]:
        row.update(home_team_id="C", home_team_abbr="C", home_team_name="Team C",
                   away_team_id="D", away_team_abbr="D", away_team_name="Team D")
    _, report = train_and_evaluate_sport(raw, "NFL")
    form = report["methods"][METHODS[1]]
    assert form["coverage"] == 0.75
    assert len(form["skipped_insufficient_history"]) == 1
    assert report["methods"]["logistic_regression"]["coverage"] == 1
    assert len(report["common_cohort_match_ids"]) == 3
    for method in report["methods"].values():
        assert sum(sum(row) for row in method["common_cohort_metrics"]["confusion_matrix"]) == 3


def test_no_labeled_test_records_has_no_fabricated_metrics():
    raw = records()
    for row in raw[24:]:
        row["home_score"] = row["away_score"] = 1
    _, report = train_and_evaluate_sport(raw, "NFL")
    assert report["excluded_test_ties"] == 6
    assert report["labeled_test_rows"] == 0
    assert all(method["metrics"] is None and method["coverage"] is None for method in report["methods"].values())


def test_delayed_results_rejected_and_future_results_do_not_affect_earlier_predictions():
    raw = records()
    data = dataset()
    model = train_historical_model(data)
    raw[-1]["home_score"] = 100
    changed = build_sport_feature_dataset(raw, "NFL")
    assert train_historical_model(changed).metadata == model.metadata
    assert model.predict(data.test, schema_version=SCHEMA_VERSION) == model.predict(changed.test, schema_version=SCHEMA_VERSION)
    raw[0]["result_available_at"] = raw[-1]["result_available_at"]
    with pytest.raises(ValueError, match="unavailable"):
        train_and_evaluate_sport(raw, "NFL")


def test_mutated_preprocessor_is_not_saved_as_compatible_model(tmp_path):
    model = train_historical_model(dataset())
    model.pipeline.named_steps["scaler"].with_mean = False
    with pytest.raises(ValueError, match="pipeline does not match"):
        save_historical_model(model, tmp_path)


def test_model_identifier_changes_with_training_data_and_no_labeled_train_is_rejected():
    data = dataset()
    original = train_historical_model(data)
    changed = dataset()
    changed.train["home_recent5_avg_scored"] = changed.train["home_recent5_avg_scored"] + 1
    assert train_historical_model(changed).metadata["model_version"] != original.metadata["model_version"]
    data.train["outcome"] = None
    with pytest.raises(InsufficientHistoryError):
        train_historical_model(data)


def test_unsupported_sport_and_empty_prediction_are_explicit_errors():
    with pytest.raises(ValueError, match="sport"):
        train_and_evaluate_sport(records(), "NBA")
    data = dataset()
    model = train_historical_model(data)
    with pytest.raises(ValueError, match="nonempty"):
        model.predict(data.test.iloc[:0], schema_version=SCHEMA_VERSION)



def test_changed_coefficients_cannot_retain_original_model_identity():
    data = dataset()
    model = train_historical_model(data)
    model.pipeline.named_steps["classifier"].coef_[0, 0] += 1
    with pytest.raises(ValueError, match="pipeline does not match"):
        model.predict(data.test, schema_version=SCHEMA_VERSION)
