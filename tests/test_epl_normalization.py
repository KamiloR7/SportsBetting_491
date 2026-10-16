"""Offline Premier League normalization across both provider formats."""
import csv
import io

import pytest

from uefa_collector import UEFACollector
from test_uefa_collector import make_premier_league_teams_payload, make_premier_league_matches_payload
from src.normalizers.multi_sport_normalizer import (
    MATCH_FIELDS, NormalizationError, normalize_epl_match, normalize_epl_matches,
    normalize_match_row, normalize_matches, normalize_teams, validate_cross_references,
)


@pytest.fixture
def collected():
    return UEFACollector(competition_code="PL",
                         team_loader=lambda _: make_premier_league_teams_payload(),
                         match_loader=lambda _: make_premier_league_matches_payload()).collect(2026)


@pytest.fixture
def org_row(collected):
    return collected.games[0]


@pytest.fixture
def csv_row():
    text = "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR\nE0,11/08/2023,Burnley,Man City,0,3,A\n"
    return next(csv.DictReader(io.StringIO(text)))


def test_collector_preservation(collected, org_row):
    row = normalize_epl_match(org_row)
    assert tuple(row) == MATCH_FIELDS
    assert (row["sport"], row["league"]) == ("SOCCER", "EPL")
    for field in ("game_id", "source", "home_team_id", "away_team_id", "home_team_name",
                  "away_team_name", "home_team_abbr", "away_team_abbr", "season", "week", "location"):
        assert row[field] == org_row[field]
    assert row["outcome"] == "HOME_WIN"
    assert row["kickoff_utc"].endswith("Z")
    assert row["kickoff_precision"] == "timestamp"
    assert row["source_season"] == "2026"
    assert normalize_match_row(org_row) == row
    assert normalize_epl_match(row) == row
    assert validate_cross_references(normalize_teams(collected.teams), normalize_matches(collected.games))


@pytest.mark.parametrize("home,away,outcome", [(2, 1, "HOME_WIN"), (0, 0, "DRAW"), (1, 3, "AWAY_WIN")])
def test_all_outcomes_both_formats(org_row, csv_row, home, away, outcome):
    org = dict(org_row, home_score=home, away_score=away, winner_team_id=None, winner_team_abbr=None)
    raw = dict(csv_row, FTHG=str(home), FTAG=str(away), FTR={"HOME_WIN": "H", "DRAW": "D", "AWAY_WIN": "A"}[outcome])
    for row in (normalize_epl_match(org), normalize_epl_match(raw, season="2023-24")):
        assert row["outcome"] == outcome
        if outcome == "DRAW":
            assert row["winner_team_id"] is None
            assert row["winner_team_abbr"] == "DRAW"
        else:
            side = "home" if outcome == "HOME_WIN" else "away"
            assert row["winner_team_id"] == row[f"{side}_team_id"]


def test_legacy_collector_draw(org_row):
    row = normalize_epl_match(dict(org_row, home_score=1, away_score=1, winner_team_id=None, winner_team_abbr="TIE"))
    assert row["outcome"] == "DRAW"


def test_scheduled(collected):
    row = normalize_epl_match(collected.games[1])
    assert row["status"] == "scheduled"
    assert row["outcome"] is None and row["home_score"] is None


@pytest.mark.parametrize("season", [2023, "2023-24", "2023/2024", "2324"])
def test_seasons_and_date_only(csv_row, season):
    row = normalize_epl_match(csv_row, season=season)
    assert row["season"] == 2023
    assert row["source_season"] == str(season)
    assert row["game_date"] == "2023-08-11"
    assert row["kickoff_utc"] is None
    assert row["kickoff_precision"] == "date"
    assert row["home_team_id"].startswith("football-data.co.uk:team:")
    assert row["home_team_abbr"] is None


@pytest.mark.parametrize("day,expected", [("11/08/2023", "2023-08-11T19:00:00Z"), ("11/12/2023", "2023-12-11T20:00:00Z")])
def test_csv_london_time(csv_row, day, expected):
    row = normalize_epl_match(dict(csv_row, Date=day, Time="20:00"), season=2023)
    assert row["kickoff_utc"] == expected
    assert row["kickoff_precision"] == "timestamp"


def test_offset_and_venue(org_row):
    row = normalize_epl_match(dict(org_row, kickoff_utc="2026-09-16T15:00:00-04:00", neutral_site=True))
    assert row["kickoff_utc"] == "2026-09-16T19:00:00Z"
    assert row["neutral_site"] is True
    assert row["location"] == org_row["location"]


@pytest.mark.parametrize("updates", [
    {"Div": "E1"}, {"Date": "31/02/2023"}, {"Date": "bad"},
    {"HomeTeam": ""}, {"AwayTeam": "Burnley"},
    {"FTHG": -1}, {"FTAG": "1.2"}, {"FTHG": None},
    {"FTHG": float("nan")}, {"FTHG": True}, {"FTR": "H"},
    {"Time": "25:00"}, {"Season": "2023-25"},
])
def test_invalid_csv(csv_row, updates):
    with pytest.raises(NormalizationError):
        normalize_epl_match(dict(csv_row, **updates), season=2023)


@pytest.mark.parametrize("updates", [
    {"game_id": []}, {"source": None}, {"home_team_id": None},
    {"away_team_name": ""}, {"game_date": "2026-02-30"},
    {"kickoff_utc": "2026-09-16T19:00:00"}, {"kickoff_utc": "bad"},
    {"home_score": -1}, {"winner_team_id": "wrong"},
    {"winner_team_abbr": "DRAW"}, {"outcome": "AWAY_WIN"},
    {"league": "UEFA Champions League"}, {"sport": "NFL"},
    {"kickoff_precision": "date"}, {"neutral_site": "perhaps"},
])
def test_invalid_collector(org_row, updates):
    with pytest.raises(NormalizationError):
        normalize_epl_match(dict(org_row, **updates))


def test_deduplicate(org_row, csv_row):
    assert len(normalize_epl_matches([org_row, org_row])) == 1
    assert len(normalize_epl_matches([csv_row, csv_row], season=2023)) == 1
    assert len(normalize_matches([org_row, dict(org_row, source="another-provider")])) == 2
    for normalize in (normalize_epl_matches, normalize_matches):
        with pytest.raises(NormalizationError, match="Conflicting duplicate"):
            normalize([org_row, dict(org_row, location="Other venue")])


@pytest.mark.parametrize("timed", [True, False])
def test_csv_roundtrip(csv_row, timed):
    row = normalize_epl_match(dict(csv_row, Time="20:00" if timed else ""), season="2023-24")
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=MATCH_FIELDS)
    writer.writeheader()
    writer.writerow(row)
    buffer.seek(0)
    assert normalize_match_row(next(csv.DictReader(buffer))) == row


def test_missing_context_and_wrong_record(csv_row):
    with pytest.raises(NormalizationError, match="season"):
        normalize_epl_match(csv_row)
    with pytest.raises(NormalizationError, match="mapping"):
        normalize_epl_match(None)


def test_csv_short_date_and_scheduled(csv_row):
    row = normalize_epl_match(dict(csv_row, Date="11/08/23", FTHG="", FTAG="", FTR="", status="scheduled"), season=2023)
    assert row["game_date"] == "2023-08-11"
    assert row["outcome"] is None and row["winner_team_id"] is None


def test_csv_conflicting_duplicate_result(csv_row):
    with pytest.raises(NormalizationError, match="Conflicting duplicate"):
        normalize_epl_matches([csv_row, dict(csv_row, FTAG="4")], season=2023)


def test_date_only_collector(org_row):
    row = normalize_epl_match(dict(org_row, kickoff_utc=None, game_time_eastern=None))
    assert row["kickoff_precision"] == "date"
    assert row["kickoff_utc"] is None


def test_mocked_ingestion_contract(org_row):
    from backend.app.database.match_ingestion import upsert_match
    from backend.tests.test_match_ingestion import FakeConnection

    row = normalize_epl_match(org_row)
    conn = FakeConnection()
    assert upsert_match(conn, row) == 99
    league = next(params for sql, params in conn.calls if "SELECT id FROM leagues" in sql)
    assert league["name"] == "EPL"
    team = next(params for sql, params in conn.calls if "SELECT t.id FROM teams" in sql)
    assert team["sport_name"] == "SOCCER"
    inserted = next(params for sql, params in conn.calls if "INSERT INTO matches" in sql)
    assert inserted["status"] == "final"
