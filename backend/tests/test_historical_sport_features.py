"""Synthetic feature contracts, not evidence of historical model accuracy."""
from copy import deepcopy
from datetime import date, timedelta
import json

import numpy as np
import pandas as pd
import pytest

from app.ml.features.historical_sport_features import (
    METADATA_COLUMNS, SCHEMA_VERSION, build_sport_feature_dataset, feature_columns,
)


def match(day, home="A", away="B", home_score=3, away_score=1, sport="NFL", season=2024):
    calendar = (date(season, 1, 1) + timedelta(days=day - 1)).isoformat()
    return dict(
        game_id=str(day), source="synthetic-features", sport=sport, league=sport,
        season=season, week=day, game_date=calendar,
        kickoff_utc=f"{calendar}T18:00:00Z", feature_as_of=f"{calendar}T17:00:00Z",
        result_available_at=f"{calendar}T22:00:00Z", status="completed",
        home_team_id=home, away_team_id=away,
        home_team_abbr=home, away_team_abbr=away,
        home_team_name=f"Team {home}", away_team_name=f"Team {away}",
        home_score=home_score, away_score=away_score,
    )


def history(sport="NFL", length=12):
    rows = []
    for day in range(1, length + 1):
        a_score, b_score = day, 6 if sport != "MLB" else 0
        if day % 2:
            rows.append(match(day, home_score=a_score, away_score=b_score, sport=sport))
        else:
            rows.append(match(day, "B", "A", b_score, a_score, sport=sport))
    return rows


def all_features(result):
    return pd.concat([result.train, result.test], ignore_index=True)


def test_last5_and_last10_form_scoring_and_margin():
    result = build_sport_feature_dataset(history(), "NFL", 0.25)
    final = result.test.iloc[-1]  # A away, day 12; history is days 1..11.
    assert final.away_recent5_matches == 5
    assert final.away_recent5_win_rate == 1
    assert final.away_recent5_avg_scored == 9
    assert final.away_recent5_avg_conceded == 6
    assert final.away_recent5_avg_margin == 3
    assert final.away_recent10_matches == 10
    assert final.away_recent10_win_rate == 0.5
    assert final.away_recent10_avg_scored == 6.5
    assert final.away_recent10_avg_margin == 0.5


def test_venue_statistics_use_the_matching_home_and_away_history():
    final = build_sport_feature_dataset(history(), "NFL").test.iloc[-1]
    # Prior away games of A: 2,4,6,8,10. B's home games are those same fixtures.
    assert final.away_venue_matches == 5
    assert final.away_venue_win_rate == 0.4
    assert final.away_venue_avg_scored == 6
    assert final.away_venue_avg_conceded == 6
    assert final.home_venue_matches == 5
    assert final.home_venue_win_rate == 0.4
    assert final.home_venue_avg_margin == 0


def test_nfl_season_statistics_preserve_ties_and_undefined_binary_labels():
    result = build_sport_feature_dataset(history(), "NFL")
    final = result.test.iloc[-1]
    assert final.away_season_matches == 11
    assert final.away_season_wins == 5
    assert final.away_season_losses == 5
    assert final.away_season_ties == 1
    assert final.away_season_win_rate == pytest.approx(5 / 11)
    assert final.away_season_avg_scored == 6
    assert final.away_season_avg_conceded == 6
    assert final.away_season_avg_margin == 0
    assert pd.isna(all_features(result).query('source_game_id == "6"').iloc[0].outcome)


def test_epl_draws_and_points_per_match_remain_three_way():
    result = build_sport_feature_dataset(history("EPL"), "EPL")
    final = result.test.iloc[-1]
    assert final.away_season_draws == 1
    assert final.away_season_losses == 5
    assert final.away_season_points_per_match == pytest.approx(16 / 11)
    assert all_features(result).query('source_game_id == "6"').iloc[0].outcome == "draw"
    assert set(all_features(result).outcome) == {"home_win", "away_win", "draw"}
    assert "away_season_ties" not in result.feature_columns


@pytest.mark.parametrize("sport", ["NFL", "MLB", "EPL"])
def test_supported_sport_schema_determinism_and_input_immutability(sport):
    rows = history(sport)
    original = deepcopy(rows)
    result = build_sport_feature_dataset(rows, sport.lower())
    reordered = build_sport_feature_dataset(iter(rows[::-1]), sport)
    pd.testing.assert_frame_equal(result.train, reordered.train)
    pd.testing.assert_frame_equal(result.test, reordered.test)
    assert result.feature_columns == feature_columns(sport)
    assert list(result.train) == METADATA_COLUMNS + result.feature_columns + ["outcome"]
    assert result.schema_version == SCHEMA_VERSION
    assert result.train.game_date.max() < result.test.game_date.min()
    assert set(result.feature_columns).isdisjoint(METADATA_COLUMNS + ["outcome", "home_score", "away_score"])
    assert rows == original


def test_missing_history_is_nan_with_zero_counts_and_partial_windows_are_explicit():
    frames = all_features(build_sport_feature_dataset(history(), "NFL"))
    first, second = frames.iloc[0], frames.iloc[1]
    assert first.home_season_matches == 0
    assert first.home_season_wins == 0
    assert np.isnan(first.home_recent5_win_rate)
    assert np.isnan(first.home_venue_avg_scored)
    assert first.home_opponent_observations == 0
    assert np.isnan(first.home_opponent_win_rate)
    assert second.away_recent5_matches == 1
    assert second.away_recent10_matches == 1
    assert second.away_venue_matches == 0
    assert second.away_recent5_avg_scored == 1


def test_season_boundaries_reset_recent_venue_and_season_statistics():
    rows = history(length=4)
    next_season = match(1, season=2025)
    next_season["game_id"] = "new-season"
    rows.append(next_season)
    final = build_sport_feature_dataset(rows, "NFL").test.iloc[-1]
    assert final.season == 2025
    assert final.home_season_matches == 0
    assert final.home_recent10_matches == 0
    assert final.home_venue_matches == 0
    assert np.isnan(final.home_opponent_win_rate)


def test_source_and_season_provenance_survive_feature_projection():
    rows = history("EPL")
    for row in rows:
        row["source_season"] = "2024-25"
    result = build_sport_feature_dataset(rows, "EPL")
    assert set(result.train.source) == {"synthetic-features"}
    assert set(result.train.season) == {2024}
    assert set(result.train.source_season) == {"2024-25"}
    assert json.loads(result.train.iloc[0].home_team) == ["synthetic-features", "EPL", "A"]


def test_future_and_target_scores_cannot_change_their_predictors():
    rows = history()
    original = build_sport_feature_dataset(rows, "NFL")
    rows[-1]["home_score"] = 100
    changed = build_sport_feature_dataset(rows, "NFL")
    pd.testing.assert_frame_equal(original.train, changed.train)
    pd.testing.assert_frame_equal(original.test[original.feature_columns], changed.test[changed.feature_columns])
    assert original.test.iloc[-1].outcome != changed.test.iloc[-1].outcome


def test_same_day_results_are_excluded_even_when_available():
    rows = [match(1), match(2), match(3)]
    rows[1].update(game_date=rows[0]["game_date"], kickoff_utc="2024-01-01T23:00:00Z",
                   feature_as_of="2024-01-01T22:30:00Z", result_available_at="2024-01-02T02:00:00Z")
    frames = all_features(build_sport_feature_dataset(rows, "NFL"))
    assert frames.iloc[1].home_season_matches == 0
    assert frames.iloc[2].home_season_matches == 2


def test_rolling_test_history_can_use_earlier_available_test_results():
    result = build_sport_feature_dataset(history(), "NFL", 0.25)
    assert result.test.iloc[0].away_season_matches == 9
    assert result.test.iloc[-1].away_season_matches == 11


@pytest.mark.parametrize("field,value,reason", [
    ("result_available_at", None, "timezone-aware"),
    ("result_available_at", "2024-01-03T22:00:00Z", "unavailable"),
    ("feature_as_of", "2024-01-01T18:00:00Z", "before match kickoff"),
])
def test_reuses_availability_and_cutoff_validation(field, value, reason):
    rows = history()
    rows[0][field] = value
    with pytest.raises(ValueError, match=reason):
        build_sport_feature_dataset(rows, "NFL")


def test_opponent_strength_excludes_focal_team_and_unavailable_other_results():
    # A beat B; B beat C; A next faces D. B's non-A win rate is 1.
    rows = [match(1, "A", "B"), match(2, "B", "C"), match(3, "A", "D"), match(4, "C", "D")]
    result = build_sport_feature_dataset(rows, "NFL", 0.25)
    target = all_features(result).query('source_game_id == "3"').iloc[0]
    assert target.home_opponent_win_rate == 1
    assert target.home_opponent_observations == 1
    # B-C is not direct A/D history, so it may be delayed without changing A's
    # direct form. It must then be absent from A's opponent-strength calculation.
    rows[1]["result_available_at"] = "2024-01-03T20:00:00Z"
    target = all_features(build_sport_feature_dataset(rows, "NFL", 0.25)).query('source_game_id == "3"').iloc[0]
    assert target.home_season_matches == 1
    assert target.home_opponent_observations == 0
    assert np.isnan(target.home_opponent_win_rate)


def test_missing_opponent_external_history_is_not_fabricated():
    final = build_sport_feature_dataset(history(), "NFL").test.iloc[-1]
    assert final.away_opponent_observations == 0
    assert np.isnan(final.away_opponent_win_rate)


@pytest.mark.parametrize("sport", ["NBA", "UEFA", None])
def test_rejects_unsupported_sport(sport):
    with pytest.raises(ValueError):
        build_sport_feature_dataset(history(), sport)


def test_rejects_incomplete_or_duplicate_history():
    rows = history()
    with pytest.raises(ValueError, match="integrity"):
        build_sport_feature_dataset(rows + [rows[0]], "NFL")
    del rows[0]["home_score"]
    with pytest.raises(ValueError, match="integrity"):
        build_sport_feature_dataset(rows, "NFL")



def test_doubleheader_window_uses_actual_kickoff_order_not_lexical_id():
    rows = history("MLB", length=6)
    later = match(1, home_score=100, away_score=0, sport="MLB")
    later.update(game_id="0", kickoff_utc="2024-01-01T23:00:00Z",
                 feature_as_of="2024-01-01T22:30:00Z", result_available_at="2024-01-02T02:00:00Z")
    rows.append(later)
    final = build_sport_feature_dataset(rows, "MLB").test.iloc[-1]
    assert final.away_recent5_matches == 5
    assert final.away_recent5_avg_scored == pytest.approx(22.8)


def test_new_teams_with_no_history_do_not_inherit_other_teams_statistics():
    rows = history(length=4) + [match(5, "C", "D")]
    final = build_sport_feature_dataset(rows, "NFL").test.iloc[-1]
    assert final.home_season_matches == 0
    assert final.away_recent10_matches == 0
    assert np.isnan(final.home_season_win_rate)
    assert np.isnan(final.away_venue_avg_margin)


def test_opponent_strength_averages_known_opponents_per_encounter():
    rows = [match(1, "B", "C"), match(2, "A", "B"),
            match(3, "A", "C"), match(4, "A", "D"), match(5, "D", "E")]
    target = all_features(build_sport_feature_dataset(rows, "NFL")).query('source_game_id == "4"').iloc[0]
    # B beat C; excluding A games leaves B at 1 and C at 0.
    assert target.home_opponent_win_rate == 0.5
    assert target.home_opponent_observations == 2


def test_negative_margins_are_valid_predictors_and_all_predictors_are_numeric():
    result = build_sport_feature_dataset(history(), "NFL")
    frame = all_features(result)
    assert frame.iloc[1].away_season_avg_margin == -5
    assert all(pd.api.types.is_numeric_dtype(frame[column]) for column in result.feature_columns)
    assert not np.isinf(frame[result.feature_columns].to_numpy(dtype=float)).any()
