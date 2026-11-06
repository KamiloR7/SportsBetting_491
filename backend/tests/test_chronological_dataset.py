"""Synthetic contract tests; these do not measure real model performance."""
from copy import deepcopy

import pandas as pd
import pytest

from app.ml.features.chronological_dataset import build_chronological_dataset
from app.ml.features.engineer_multisport_features import FEATURE_COLUMNS, create_features


def history(sport="NFL"):
    return [dict(
        game_id=str(day), source="synthetic", league=sport,
        sport={"NFL": "American Football", "MLB": "BASEBALL", "EPL": "SOCCER"}[sport],
        season=2024, week=day, home_team_id="H", away_team_id="A",
        home_team_abbr="H", away_team_abbr="A",
        home_team_name="Home", away_team_name="Away", status="completed",
        game_date=f"2024-09-0{day}", kickoff_utc=f"2024-09-0{day}T18:00:00Z",
        feature_as_of=f"2024-09-0{day}T17:00:00Z",
        result_available_at=f"2024-09-0{day}T22:00:00Z",
        home_score=3, away_score=1,
    ) for day in range(1, 5)]


@pytest.mark.parametrize("sport", ["NFL", "MLB", "EPL"])
def test_deterministic_chronological_projection(sport):
    rows = history(sport)
    original = deepcopy(rows)
    result = build_chronological_dataset(rows, sport, 0.5)
    shuffled = build_chronological_dataset(rows[::-1], sport, 0.5)
    pd.testing.assert_frame_equal(result.train, shuffled.train)
    pd.testing.assert_frame_equal(result.test, shuffled.test)
    assert result.train.game_date.max() < result.test.game_date.min()
    assert result.train.result_available_at.max() <= result.test.feature_as_of.min()
    assert result.train.source_game_id.tolist() == ["1", "2"]
    assert rows == original


@pytest.mark.parametrize("field,value,reason", [
    ("feature_as_of", None, "timezone-aware"),
    ("result_available_at", None, "timezone-aware"),
    ("feature_as_of", "2024-09-01T18:00:00Z", "before match kickoff"),
    ("result_available_at", "2024-09-01T18:00:00Z", "follow kickoff"),
    ("kickoff_utc", None, "timezone-aware"),
    ("home_score", -1, "integrity"),
    ("status", "scheduled", "integrity|completed"),
])
def test_rejects_invalid_history(field, value, reason):
    rows = history()
    rows[0][field] = value
    with pytest.raises(ValueError, match=reason):
        build_chronological_dataset(rows, "NFL")


def test_rejects_delayed_training_labels_even_for_unrelated_teams():
    rows = history()
    rows[0].update(home_team_id="X", away_team_id="Y",
                   result_available_at="2024-09-04T18:00:00Z")
    with pytest.raises(ValueError, match="Training labels unavailable"):
        build_chronological_dataset(rows, "NFL", 0.5)


def test_rejects_unavailable_prior_result_in_rolling_test_history():
    rows = history()
    rows[2]["result_available_at"] = "2024-09-04T18:00:00Z"
    with pytest.raises(ValueError, match="unavailable at prediction time"):
        build_chronological_dataset(rows, "NFL", 0.5)


@pytest.mark.parametrize("conflicting", [False, True])
def test_rejects_duplicate_history(conflicting):
    rows = history()
    duplicate = dict(rows[0])
    if conflicting:
        duplicate["home_score"] = 4
    with pytest.raises(ValueError, match="integrity"):
        build_chronological_dataset(rows + [duplicate], "NFL")


def test_rejects_mixed_sources_and_sports():
    rows = history()
    rows[1]["source"] = "other"
    with pytest.raises(ValueError, match="one provider"):
        build_chronological_dataset(rows, "NFL")
    with pytest.raises(ValueError, match="selected sport"):
        build_chronological_dataset(history("EPL"), "NFL")


def test_same_utc_day_stays_in_one_partition():
    rows = history()
    rows[2].update(game_date="2024-09-02", kickoff_utc="2024-09-02T23:00:00Z",
                   feature_as_of="2024-09-02T22:30:00Z", result_available_at="2024-09-03T02:00:00Z")
    result = build_chronological_dataset(rows, "NFL", 0.5)
    assert result.train.source_game_id.tolist() == ["1"]
    assert set(result.test.source_game_id) == {"2", "3", "4"}


@pytest.mark.parametrize("fraction", [0, 1, float("nan")])
def test_rejects_invalid_split_fraction(fraction):
    with pytest.raises(ValueError, match="test_fraction"):
        build_chronological_dataset(history(), "NFL", fraction)


def test_rejects_empty_and_unsupported_inputs():
    with pytest.raises(ValueError, match="empty"):
        build_chronological_dataset([], "NFL")
    with pytest.raises(ValueError, match="Unsupported sport"):
        build_chronological_dataset(history(), "NBA")


def test_test_score_changes_do_not_change_training_partition():
    rows = history()
    before = build_chronological_dataset(rows, "NFL", 0.5)
    rows[3]["home_score"] = 20
    after = build_chronological_dataset(rows, "NFL", 0.5)
    pd.testing.assert_frame_equal(before.train, after.train)


@pytest.mark.parametrize("value", ["not-a-time", "2024-09-01T22:00:00", pd.NaT, float("nan")])
def test_rejects_invalid_result_availability(value):
    rows = history()
    rows[0]["result_available_at"] = value
    with pytest.raises(ValueError):
        build_chronological_dataset(rows, "NFL")


def test_label_available_exactly_at_test_cutoff_is_eligible():
    rows = history()
    rows[1]["result_available_at"] = rows[2]["feature_as_of"]
    result = build_chronological_dataset(rows, "NFL", 0.5)
    assert len(result.train) == 2


def test_preserves_source_season_label():
    rows = history("EPL")
    for row in rows:
        row["source_season"] = "2024-25"
    result = build_chronological_dataset(rows, "EPL")
    assert set(result.train.source) == {"synthetic"}
    assert set(result.train.season) == {2024}
    assert set(result.train.source_season) == {"2024-25"}
    assert result.train.game_id.is_unique


def test_rolling_features_ignore_future_and_same_day_scores():
    rows = history()
    rows[1].update(game_date="2024-09-01", kickoff_utc="2024-09-01T23:00:00Z",
                   feature_as_of="2024-09-01T22:30:00Z", result_available_at="2024-09-02T02:00:00Z")
    result = build_chronological_dataset(rows, "NFL", 0.5)
    features = create_features(pd.concat([result.train, result.test]))
    assert features.loc[0, "home_avg_score"] == 0
    assert features.loc[1, "home_avg_score"] == 0
    assert features.loc[2, "home_avg_score"] == 3
    assert features.loc[2, "home_win_rate"] == 1
    rows[3]["home_score"] = 20
    changed = build_chronological_dataset(rows, "NFL", 0.5)
    changed_features = create_features(pd.concat([changed.train, changed.test]))
    pd.testing.assert_frame_equal(features[FEATURE_COLUMNS], changed_features[FEATURE_COLUMNS])


def test_rejects_history_with_only_one_utc_day():
    rows = history()[:2]
    rows[1].update(game_date=rows[0]["game_date"], kickoff_utc=rows[0]["kickoff_utc"],
                   feature_as_of=rows[0]["feature_as_of"], result_available_at=rows[0]["result_available_at"])
    with pytest.raises(ValueError, match="distinct game dates"):
        build_chronological_dataset(rows, "NFL")


def test_equivalent_offset_timestamps_produce_same_utc_partition():
    rows = history()
    before = build_chronological_dataset(rows, "NFL", 0.5)
    rows[1]["kickoff_utc"] = "2024-09-02T11:00:00-07:00"
    after = build_chronological_dataset(rows, "NFL", 0.5)
    pd.testing.assert_frame_equal(before.train, after.train)


@pytest.mark.parametrize("sport", [None, 1])
def test_rejects_nontext_sport(sport):
    with pytest.raises(ValueError, match="Sport must be"):
        build_chronological_dataset(history(), sport)


def test_rejects_inferred_mlb_season():
    rows = history("MLB")
    del rows[0]["season"]
    with pytest.raises(ValueError, match="explicit season provenance"):
        build_chronological_dataset(rows, "MLB")


def test_rejects_valid_nonfinal_record():
    rows = history()
    rows[0].update(status="scheduled", home_score=None, away_score=None)
    with pytest.raises(ValueError, match="Only completed"):
        build_chronological_dataset(rows, "NFL")


def test_training_features_cannot_use_late_training_result():
    rows = history()
    rows[0]["result_available_at"] = "2024-09-02T18:00:00Z"
    with pytest.raises(ValueError, match="unavailable at prediction time"):
        build_chronological_dataset(rows, "NFL", 0.5)


@pytest.mark.parametrize("sport", ["NFL", "EPL"])
def test_retains_ties_for_downstream_sport_specific_labeling(sport):
    rows = history(sport)
    rows[0]["away_score"] = rows[0]["home_score"]
    result = build_chronological_dataset(rows, sport, 0.5)
    assert result.train.iloc[0].home_score == result.train.iloc[0].away_score


def test_train_features_equal_features_from_full_chronological_history():
    result = build_chronological_dataset(history(), "NFL", 0.5)
    train_features = create_features(result.train)
    all_features = create_features(pd.concat([result.train, result.test]))
    pd.testing.assert_frame_equal(train_features, all_features.iloc[:len(train_features)])
