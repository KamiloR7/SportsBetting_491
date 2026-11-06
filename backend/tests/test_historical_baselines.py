"""Synthetic tests establish algorithm behavior, not real-data accuracy."""
from copy import deepcopy
import math

import numpy as np
import pandas as pd
import pytest

from app.ml.evaluation.evaluate_historical_baselines import evaluate_baselines
from app.ml.features.historical_sport_features import build_sport_feature_dataset
from app.ml.historical_baselines import BaselinePredictor, InsufficientHistoryError, METHODS
from backend.tests.test_historical_sport_features import history, match


def sample(sport="NFL"):
    return build_sport_feature_dataset(history(sport), sport, 0.25)


def test_home_frequency_uses_training_outcomes_only_and_excludes_nfl_ties():
    dataset = sample()
    baseline = BaselinePredictor.fit(dataset)
    # Training days 1..9: home wins on 2,4,7,9; away wins 1,3,5,8; day 6 tied.
    assert baseline.class_counts == (4, 4)
    assert baseline.excluded_training_ties == 1
    assert baseline.probabilities == {"home_win": 0.5, "away_win": 0.5}
    predictions = baseline.predict(dataset.test, METHODS[0], schema_version=dataset.schema_version)
    assert all(row["probabilities"] == baseline.probabilities for row in predictions)
    assert all(row["predicted_outcome"] == "home_win" for row in predictions)


def test_epl_frequency_preserves_draw_class_and_empirical_frequency():
    baseline = BaselinePredictor.fit(sample("EPL"))
    assert baseline.class_counts == (4, 1, 4)
    assert baseline.probabilities == {"home_win": 4 / 9, "draw": 1 / 9, "away_win": 4 / 9}


def test_team_form_formula_is_hand_calculable():
    dataset = sample()
    baseline = BaselinePredictor.fit(dataset)
    final = dataset.test.iloc[[-1]].copy()
    # Equal season form with balanced season records and opposite scoring form.
    for side in ("home", "away"):
        final[f"{side}_season_matches"] = 2
        final[f"{side}_season_wins"] = 1
        final[f"{side}_season_losses"] = 1
        final[f"{side}_season_ties"] = 0
        final[f"{side}_recent5_matches"] = 2
    final["home_recent5_avg_scored"] = 3
    final["home_recent5_avg_conceded"] = 1
    final["home_recent5_avg_margin"] = 2
    final["away_recent5_avg_scored"] = 1
    final["away_recent5_avg_conceded"] = 3
    final["away_recent5_avg_margin"] = -2
    # margin contrast=4/8, signal=0.25, p_home=0.625.
    result = baseline.predict(final, METHODS[1], schema_version=dataset.schema_version)[0]
    assert result["probabilities"] == {"home_win": 0.625, "away_win": 0.375}


def test_epl_team_form_assigns_empirical_draw_rate_to_equal_strength():
    dataset = sample("EPL")
    baseline = BaselinePredictor.fit(dataset)
    final = dataset.test.iloc[[-1]].copy()
    for side in ("home", "away"):
        final[f"{side}_season_matches"] = 2
        final[f"{side}_season_wins"] = 1
        final[f"{side}_season_losses"] = 0
        final[f"{side}_season_draws"] = 1
        final[f"{side}_recent5_matches"] = 2
        final[f"{side}_recent5_avg_scored"] = 2
        final[f"{side}_recent5_avg_conceded"] = 2
        final[f"{side}_recent5_avg_margin"] = 0
    probs = baseline.predict(final, METHODS[1], schema_version=dataset.schema_version)[0]["probabilities"]
    assert probs["draw"] == pytest.approx(1 / 9)
    assert probs["home_win"] == pytest.approx(4 / 9)
    assert probs["away_win"] == pytest.approx(4 / 9)


@pytest.mark.parametrize("sport", ["NFL", "MLB", "EPL"])
@pytest.mark.parametrize("method", METHODS)
def test_valid_deterministic_prediction_contract(sport, method):
    dataset = sample(sport)
    baseline = BaselinePredictor.fit(dataset)
    original = dataset.test.copy(deep=True)
    first = baseline.predict(dataset.test, method, schema_version=dataset.schema_version)
    second = baseline.predict(dataset.test, method, schema_version=dataset.schema_version)
    assert first == second
    pd.testing.assert_frame_equal(dataset.test, original)
    for result in first:
        assert result["sport"] == sport
        assert result["baseline_method"] == method
        assert result["feature_schema_version"] == dataset.schema_version
        probabilities = result["probabilities"]
        assert all(math.isfinite(p) and 0 <= p <= 1 for p in probabilities.values())
        assert abs(sum(probabilities.values()) - 1) <= 1e-6
        assert result["predicted_outcome"] == max(probabilities, key=probabilities.get)


def test_all_tie_training_history_is_insufficient_not_away_wins():
    rows = history()
    for row in rows:
        row["home_score"] = row["away_score"] = 1
    with pytest.raises(InsufficientHistoryError, match="labeled training"):
        BaselinePredictor.fit(build_sport_feature_dataset(rows, "NFL"))


def test_cold_start_errors_for_form_but_not_frequency():
    rows = history(length=4) + [match(5, "C", "D")]
    dataset = build_sport_feature_dataset(rows, "NFL")
    baseline = BaselinePredictor.fit(dataset)
    with pytest.raises(InsufficientHistoryError, match="team history"):
        baseline.predict(dataset.test, METHODS[1], schema_version=dataset.schema_version)
    assert len(baseline.predict(dataset.test, METHODS[0], schema_version=dataset.schema_version)) == 1


@pytest.mark.parametrize("field,value", [
    ("home_season_wins", -1), ("home_season_matches", 1.5),
    ("home_season_losses", 100), ("home_recent5_matches", 6),
    ("home_recent5_avg_margin", float("inf")),
    ("home_recent5_avg_scored", -1), ("home_recent5_avg_margin", 123),
    ("home_recent5_avg_scored", "3"), ("home_recent5_avg_scored", np.nan),
])
def test_rejects_invalid_form_inputs(field, value):
    dataset = sample()
    baseline = BaselinePredictor.fit(dataset)
    changed = dataset.test.copy()
    changed[field] = value
    with pytest.raises(ValueError):
        baseline.predict(changed, METHODS[1], schema_version=dataset.schema_version)


def test_rejects_missing_features_wrong_schema_or_method():
    dataset = sample()
    baseline = BaselinePredictor.fit(dataset)
    with pytest.raises(ValueError, match="Missing team-form"):
        baseline.predict(dataset.test.drop(columns="home_season_wins"), METHODS[1], schema_version=dataset.schema_version)
    with pytest.raises(ValueError, match="schema"):
        baseline.predict(dataset.test, METHODS[0], schema_version="old-v0")
    with pytest.raises(ValueError, match="method"):
        baseline.predict(dataset.test, "unknown", schema_version=dataset.schema_version)
    dataset.feature_columns = dataset.feature_columns[::-1]
    with pytest.raises(ValueError, match="ordering"):
        BaselinePredictor.fit(dataset)


def test_rejects_predictions_before_training_and_unavailable_training_labels():
    dataset = sample()
    baseline = BaselinePredictor.fit(dataset)
    with pytest.raises(ValueError, match="training UTC days"):
        baseline.predict(dataset.train, METHODS[0], schema_version=dataset.schema_version)
    changed = dataset.test.copy()
    changed["feature_as_of"] = "2024-01-01T17:00:00Z"
    with pytest.raises(ValueError, match="unavailable"):
        baseline.predict(changed, METHODS[0], schema_version=dataset.schema_version)


@pytest.mark.parametrize("field,value", [
    ("feature_as_of", "2024-01-10T18:00:00Z"),
    ("start_time", "2024-01-10T18:00:00"),
    ("sport", "NBA"), ("game_id", ""),
])
def test_rejects_invalid_prediction_metadata(field, value):
    dataset = sample()
    baseline = BaselinePredictor.fit(dataset)
    changed = dataset.test.iloc[[0]].copy()
    changed[field] = value
    with pytest.raises(ValueError):
        baseline.predict(changed, METHODS[0], schema_version=dataset.schema_version)


def test_future_labels_do_not_change_fitted_frequencies_or_earlier_predictions():
    rows = history()
    before = build_sport_feature_dataset(rows, "NFL", 0.25)
    first = BaselinePredictor.fit(before)
    rows[-1]["home_score"] = 100
    after = build_sport_feature_dataset(rows, "NFL", 0.25)
    second = BaselinePredictor.fit(after)
    assert first == second
    for method in METHODS:
        assert first.predict(before.test, method, schema_version=before.schema_version) == second.predict(after.test, method, schema_version=after.schema_version)


def test_evaluation_uses_chronological_split_and_exact_binary_macro_metrics():
    report = evaluate_baselines(history(), "NFL", 0.25)
    assert report["train_rows"] == 9
    assert report["test_rows"] == 3
    assert report["excluded_training_ties"] == 1
    assert report["train_end_day"] < report["test_start_day"]
    # Test labels are away_win, home_win, away_win; frequency predicts home_win.
    metrics = report["methods"][METHODS[0]]["metrics"]
    assert metrics["accuracy"] == pytest.approx(1 / 3)
    assert metrics["precision"] == pytest.approx(1 / 6)
    assert metrics["recall"] == pytest.approx(0.5)
    assert metrics["f1"] == pytest.approx(0.25)
    assert metrics["confusion_matrix"] == [[1, 0], [2, 0]]


def test_epl_multiclass_evaluation_has_fixed_order_and_no_collapsed_draws():
    report = evaluate_baselines(history("EPL"), "EPL", 0.25)
    metrics = report["methods"][METHODS[0]]["metrics"]
    assert metrics["class_order"] == ["home_win", "draw", "away_win"]
    assert metrics["confusion_matrix"] == [[1, 0, 0], [0, 0, 0], [2, 0, 0]]
    assert metrics["average"] == "macro"
    assert set(metrics["per_class"]) == {"home_win", "draw", "away_win"}


def test_evaluation_reports_missing_history_and_common_cohort_without_fake_metrics():
    rows = history(length=4) + [match(5, "C", "D")]
    report = evaluate_baselines(rows, "NFL")
    assert report["methods"][METHODS[0]]["evaluated_rows"] == 1
    assert report["methods"][METHODS[1]]["evaluated_rows"] == 0
    assert report["methods"][METHODS[1]]["metrics"] is None
    assert len(report["methods"][METHODS[1]]["skipped_insufficient_history"]) == 1
    assert report["common_cohort_match_ids"] == []
    assert all(row["common_cohort_metrics"] is None for row in report["methods"].values())


def test_evaluation_excludes_heldout_nfl_ties_and_handles_no_evaluable_labels():
    rows = history()
    for row in rows[9:]:
        row["home_score"] = row["away_score"] = 1
    report = evaluate_baselines(rows, "NFL", 0.25)
    assert report["excluded_test_ties"] == 3
    assert report["labeled_test_rows"] == 0
    assert all(row["metrics"] is None and row["coverage"] is None for row in report["methods"].values())


@pytest.mark.parametrize("sport", ["NFL", "MLB", "EPL"])
def test_evaluation_determinism_and_no_mutation(sport):
    rows = history(sport)
    original = deepcopy(rows)
    assert evaluate_baselines(rows, sport) == evaluate_baselines(rows[::-1], sport)
    assert rows == original


@pytest.mark.parametrize("threshold", [0, -1, True, 1.5])
def test_rejects_invalid_history_thresholds(threshold):
    with pytest.raises(ValueError, match="positive integer"):
        BaselinePredictor.fit(sample(), min_team_matches=threshold)


def test_insufficient_training_count_and_unsupported_sport():
    with pytest.raises(InsufficientHistoryError):
        BaselinePredictor.fit(sample(), min_training_matches=100)
    with pytest.raises(ValueError):
        evaluate_baselines(history(), "NBA")


def test_nfl_ties_receive_neutral_credit_in_form_not_loss_credit():
    dataset = sample()
    baseline = BaselinePredictor.fit(dataset)
    target = dataset.test.iloc[[-1]].copy()
    for side in ("home", "away"):
        target[f"{side}_season_matches"] = 2
        target[f"{side}_season_wins"] = 1
        target[f"{side}_season_losses"] = 1
        target[f"{side}_season_ties"] = 0
        target[f"{side}_recent5_matches"] = 2
        target[f"{side}_recent5_avg_scored"] = 1
        target[f"{side}_recent5_avg_conceded"] = 1
        target[f"{side}_recent5_avg_margin"] = 0
    target["home_season_losses"] = 0
    target["home_season_ties"] = 1
    result = baseline.predict(target, METHODS[1], schema_version=dataset.schema_version)[0]
    assert result["probabilities"]["home_win"] == pytest.approx(0.5625)


def test_single_class_training_is_a_valid_empirical_baseline():
    rows = [match(day, sport="MLB") for day in range(1, 7)]
    dataset = build_sport_feature_dataset(rows, "MLB")
    baseline = BaselinePredictor.fit(dataset)
    assert baseline.probabilities == {"home_win": 1, "away_win": 0}
    assert baseline.predict(dataset.test, METHODS[0], schema_version=dataset.schema_version)


def test_training_rejects_invalid_labels_and_missing_schema_columns():
    dataset = sample("EPL")
    dataset.train.loc[0, "outcome"] = None
    with pytest.raises(ValueError, match="training outcome"):
        BaselinePredictor.fit(dataset)
    dataset = sample()
    dataset.train.loc[0, "outcome"] = "draw"
    with pytest.raises(ValueError, match="training outcome"):
        BaselinePredictor.fit(dataset)
    dataset = sample()
    dataset.train = dataset.train.drop(columns=dataset.feature_columns[0])
    with pytest.raises(ValueError, match="schema"):
        BaselinePredictor.fit(dataset)


def test_form_history_threshold_and_duplicate_prediction_ids_are_explicit_errors():
    dataset = sample()
    baseline = BaselinePredictor.fit(dataset, min_team_matches=100)
    with pytest.raises(InsufficientHistoryError):
        baseline.predict(dataset.test, METHODS[1], schema_version=dataset.schema_version)
    duplicate = pd.concat([dataset.test, dataset.test.iloc[[0]]])
    with pytest.raises(ValueError, match="identifiers"):
        baseline.predict(duplicate, METHODS[0], schema_version=dataset.schema_version)


def test_heldout_draw_is_evaluated_as_draw_not_as_away_win():
    rows = history("EPL")
    rows[9]["home_score"] = rows[9]["away_score"] = 1
    report = evaluate_baselines(rows, "EPL", 0.25)
    matrix = report["methods"][METHODS[0]]["metrics"]["confusion_matrix"]
    assert matrix == [[1, 0, 0], [1, 0, 0], [1, 0, 0]]


def test_invalid_availability_rejects_evaluation_before_predictions():
    rows = history()
    rows[0]["result_available_at"] = "2024-01-12T22:00:00Z"
    with pytest.raises(ValueError, match="unavailable"):
        evaluate_baselines(rows, "NFL")
