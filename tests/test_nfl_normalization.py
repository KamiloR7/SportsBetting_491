"""Offline NFL collector -> shared normalization contract."""
import csv
import io

import pytest

from nfl_collector import NFLCollector, normalize_game, normalize_team
from test_nfl_collector import make_games, make_teams
from src.normalizers.multi_sport_normalizer import (
    MATCH_FIELDS, NormalizationError, normalize_match_row, normalize_matches,
    normalize_nfl_match, normalize_nfl_matches, normalize_teams,
    validate_cross_references,
)


@pytest.fixture
def nfl_row():
    return NFLCollector(team_loader=make_teams, schedule_loader=lambda _: make_games()).collect(2025).games[0]


def test_collector_and_canonical_input(nfl_row):
    row = normalize_nfl_match(nfl_row)
    assert tuple(row) == MATCH_FIELDS
    assert row["sport"] == "American Football"
    assert row["league"] == "NFL"
    for field in ("source", "game_id", "home_team_id", "away_team_id", "home_team_abbr",
                  "away_team_abbr", "home_team_name", "away_team_name", "season", "week",
                  "game_date", "home_score", "away_score", "status"):
        assert row[field] == nfl_row[field]
    assert row["kickoff_utc"] == "2025-09-08T00:20:00Z"
    assert row["winner_team_id"] == "ID-BUF"
    assert normalize_match_row(nfl_row) == row
    assert normalize_nfl_match(row) == row
    teams = normalize_teams([normalize_team(t) for t in make_teams()])
    assert len(validate_cross_references(teams, [row])) == 5


@pytest.mark.parametrize("home,away,winner,abbr", [(35, 30, "ID-BAL", "BAL"), (20, 20, None, "TIE")])
def test_derive_outcome(nfl_row, home, away, winner, abbr):
    row = normalize_nfl_match(dict(nfl_row, home_score=home, away_score=away,
                                   winner_team_id=None, winner_team_abbr=None))
    assert (row["winner_team_id"], row["winner_team_abbr"]) == (winner, abbr)


def test_scheduled():
    game = NFLCollector(team_loader=make_teams, schedule_loader=lambda _: make_games()).collect(2025).games[1]
    row = normalize_nfl_match(game)
    assert row["status"] == "scheduled"
    assert row["home_score"] is None and row["winner_team_id"] is None


def test_inferred_midnight_removed():
    raw = dict(make_games()[0], gametime=None)
    teams = {t["team_abbr"]: normalize_team(t) for t in make_teams()}
    collected = normalize_game(raw, teams)
    assert collected["kickoff_utc"] is not None
    row = normalize_nfl_match(collected)
    assert row["kickoff_utc"] is None
    assert row["game_date"] == raw["gameday"]
    assert normalize_nfl_match(row) == row


def test_date_only_and_explicit_timestamp(nfl_row):
    row = dict(nfl_row, game_time_eastern=None, kickoff_utc=None)
    assert normalize_nfl_match(row)["kickoff_utc"] is None
    row["kickoff_utc"] = "2025-09-07T17:20:00-07:00"
    assert normalize_nfl_match(row)["kickoff_utc"] == "2025-09-08T00:20:00Z"


@pytest.mark.parametrize("date,time,expected", [
    ("2025-12-07", "20:20", "2025-12-08T01:20:00Z"),
    ("2025-09-07", "20:20", "2025-09-08T00:20:00Z"),
])
def test_eastern_dst(nfl_row, date, time, expected):
    row = normalize_nfl_match(dict(nfl_row, game_date=date, game_time_eastern=time, kickoff_utc=None))
    assert row["kickoff_utc"] == expected


@pytest.mark.parametrize("updates,error", [
    ({"game_id": " "}, "game_id"), ({"source": None}, "source"),
    ({"home_team_id": []}, "identity"), ({"home_team_id": True}, "identity"),
    ({"away_team_id": "ID-BAL"}, "must differ"),
    ({"home_team_abbr": ""}, "home_team_abbr"),
    ({"game_date": "2025-02-30"}, "game_date"),
    ({"game_date": "bad"}, "game_date"),
    ({"kickoff_utc": "2025-09-08T00:20:00"}, "timezone"),
    ({"kickoff_utc": "bad"}, "kickoff_utc"),
    ({"kickoff_utc": "2025-09-08T01:20:00Z"}, "conflicts"),
    ({"kickoff_utc": "2025-09-09T00:20:00Z", "game_time_eastern": None}, "game_date"),
    ({"game_time_eastern": "25:00"}, "game_time_eastern"),
    ({"home_score": -1}, "nonnegative"),
    ({"home_score": "2.5"}, "integer"),
    ({"home_score": float("nan")}, "integer"),
    ({"home_score": None}, "missing a final score"),
    ({"winner_team_id": "ID-BAL"}, "conflicts"),
    ({"winner_team_abbr": "TIE"}, "conflicts"),
    ({"status": "unknown"}, "status"), ({"season": None}, "season"),
    ({"week": 0}, "week"), ({"sport": "NBA"}, "sport identity"),
])
def test_invalid(nfl_row, updates, error):
    with pytest.raises(NormalizationError, match=error):
        normalize_nfl_match(dict(nfl_row, **updates))


def test_duplicates(nfl_row):
    assert len(normalize_nfl_matches([nfl_row, nfl_row])) == 1
    assert len(normalize_matches([nfl_row, nfl_row])) == 1
    other = dict(nfl_row, source="other-provider")
    assert len(normalize_matches([nfl_row, other])) == 2
    for normalize in (normalize_matches, normalize_nfl_matches):
        with pytest.raises(NormalizationError, match="Conflicting duplicate"):
            normalize([nfl_row, dict(nfl_row, home_score=28)])


def test_csv_roundtrip(nfl_row):
    row = normalize_nfl_match(nfl_row)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=MATCH_FIELDS)
    writer.writeheader()
    writer.writerow(row)
    buffer.seek(0)
    assert normalize_nfl_match(next(csv.DictReader(buffer))) == row


def test_non_mapping():
    with pytest.raises(NormalizationError, match="mapping"):
        normalize_nfl_match(None)


def test_tie_cannot_have_winner(nfl_row):
    with pytest.raises(NormalizationError, match="conflicts"):
        normalize_nfl_match(dict(nfl_row, home_score=30))


def test_ingestion_contract_with_fake_connection(nfl_row):
    from backend.app.database.match_ingestion import upsert_match
    from backend.tests.test_match_ingestion import FakeConnection

    conn = FakeConnection()
    assert upsert_match(conn, normalize_nfl_match(nfl_row)) == 99
    team_parameters = [params for sql, params in conn.calls if "SELECT t.id FROM teams" in sql]
    assert all(params["sport_name"] == "American Football" for params in team_parameters)
    inserted = next(params for sql, params in conn.calls if "INSERT INTO matches" in sql)
    assert inserted["status"] == "final"
    assert inserted["start_time"] == "2025-09-08T00:20:00Z"
