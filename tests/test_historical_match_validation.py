"""Offline DATA-24 quality gate tests using the shared normalized contract."""
from copy import deepcopy
import json

import pytest

from src.normalizers.match_validation import validate_historical_matches
from src.normalizers.multi_sport_normalizer import MATCH_FIELDS


def record(league="NFL", **updates):
    row = dict.fromkeys(MATCH_FIELDS)
    row.update(game_id="game-1", source="fixture-provider", league=league,
               sport={"NFL": "American Football", "MLB": "BASEBALL", "EPL": "SOCCER"}[league],
               season=2024, week=1, game_date="2024-09-01",
               home_team_id="home", away_team_id="away", home_team_abbr="H", away_team_abbr="A",
               home_team_name="Home Team", away_team_name="Away Team",
               home_score=3, away_score=1, status="completed")
    row.update(updates)
    return row


@pytest.mark.parametrize("league", ["NFL", "MLB", "EPL"])
def test_valid_contract_and_no_mutation(league):
    row = record(league)
    before = deepcopy(row)
    report = validate_historical_matches([row])
    assert report.counts == {"read": 1, "accepted": 1, "rejected": 0, "duplicates": 0}
    assert tuple(report.accepted[0]) == MATCH_FIELDS
    assert report.accepted[0]["winner_team_id"] == "home"
    assert row == before
    json.dumps(report.to_dict())


@pytest.mark.parametrize("league,accepted", [("NFL", True), ("EPL", True), ("MLB", False)])
def test_ties(league, accepted):
    report = validate_historical_matches([record(league, home_score=1, away_score=1)])
    assert bool(report.accepted) == accepted
    if accepted:
        assert report.accepted[0]["winner_team_id"] is None
    if league == "EPL":
        assert report.accepted[0]["outcome"] == "DRAW"


@pytest.mark.parametrize("field,value", [
    ("game_id", None), ("game_id", " "), ("game_id", True), ("game_id", []),
    ("source", None), ("source", "nan"), ("source", "x" * 101), ("game_id", "x" * 161),
    ("source", 123), ("away_team_name", " Home Team "),
    ("home_team_id", None), ("away_team_id", "home"),
    ("sport", None), ("sport", "NBA"), ("league", "NBA"), ("league", {}),
    ("home_score", None), ("home_score", -1), ("home_score", True),
    ("away_score", float("nan")), ("away_score", "2.5"),
    ("game_date", "2024-02-30"), ("game_date", None),
    ("kickoff_utc", "2024-09-01T20:00:00"), ("kickoff_utc", "bad"),
    ("winner_team_id", "away"), ("outcome", "AWAY_WIN"), ("status", "unknown"),
])
def test_rejections_with_explicit_reasons(field, value):
    row = record()
    row[field] = value
    report = validate_historical_matches([row])
    assert report.counts["rejected"] == 1
    assert report.rejected[0]["index"] == 0
    assert report.rejected[0]["reasons"]


def test_duplicate_report():
    row = record()
    report = validate_historical_matches([row, deepcopy(row), record(game_id="game-2"), None])
    assert report.counts == {"read": 4, "accepted": 2, "rejected": 1, "duplicates": 1}
    assert report.duplicates == [{"index": 1, "kept_index": 0, "source": "fixture-provider", "game_id": "game-1"}]


def test_conflicts_reject_entire_group_in_either_order():
    one, two = record(), record(home_score=4)
    for rows in ([one, two, one], [two, one, one]):
        report = validate_historical_matches(rows)
        assert report.counts == {"read": 3, "accepted": 0, "rejected": 3, "duplicates": 0}
        assert all("conflicting duplicate" in rejection["reasons"][0] for rejection in report.rejected)


def test_source_scoping_and_database_key():
    assert len(validate_historical_matches([record(), record(source="other")]).accepted) == 2
    # Database external match mappings do not include league in their key.
    assert len(validate_historical_matches([record("NFL"), record("MLB")]).rejected) == 2


def test_normalized_equivalent_duplicates():
    report = validate_historical_matches([record(), record(home_score="3", away_score="1", status="FINAL")])
    assert report.counts["duplicates"] == 1


@pytest.mark.parametrize("league", ["NFL", "MLB", "EPL"])
def test_scheduled_and_date_only_are_valid_data(league):
    report = validate_historical_matches([record(league, home_score=None, away_score=None, status="scheduled")])
    assert report.counts["accepted"] == 1
    assert report.accepted[0]["kickoff_utc"] is None


def test_aware_offset_converted_to_utc():
    report = validate_historical_matches([record(kickoff_utc="2024-09-01T16:00:00-04:00")])
    assert report.accepted[0]["kickoff_utc"] == "2024-09-01T20:00:00Z"


def test_empty_input_and_generator():
    assert validate_historical_matches([]).counts["read"] == 0
    assert validate_historical_matches(record(game_id=str(i)) for i in range(3)).counts["accepted"] == 3


def test_invalid_rows_do_not_abort_valid_rows():
    report = validate_historical_matches([None, record(game_id=None), record(game_id="valid")])
    assert report.counts == {"read": 3, "accepted": 1, "rejected": 2, "duplicates": 0}
    assert [item["index"] for item in report.rejected] == [0, 1]
