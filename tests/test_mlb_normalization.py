"""MLB schedule and existing six-column ML export normalization, offline."""
from copy import deepcopy
import csv
import io
import json

import pytest

from src.normalizers.multi_sport_normalizer import (
    MATCH_FIELDS, NormalizationError, normalize_mlb_match, normalize_mlb_matches,
    normalize_match_row, normalize_matches,
    normalize_mlb_schedule,
)


@pytest.fixture
def game():
    return {"gamePk": 745001, "officialDate": "2024-04-01", "season": "2024",
            "gameType": "R", "gameDate": "2024-04-02T02:10:00Z",
            "status": {"detailedState": "Final"}, "neutralSite": False,
            "venue": {"id": 1, "name": "Dodger Stadium"},
            "teams": {"home": {"team": {"id": 119, "name": "Los Angeles Dodgers", "abbreviation": "LAD"}, "score": 5, "isWinner": True},
                      "away": {"team": {"id": 147, "name": "New York Yankees", "abbreviation": "NYY"}, "score": 3, "isWinner": False}}}


def test_schedule_fields(game):
    row = normalize_match_row(game)
    assert tuple(row) == MATCH_FIELDS
    assert (row["sport"], row["league"], row["source"]) == ("BASEBALL", "MLB", "statsapi.mlb.com")
    assert row["game_id"] == "745001"
    assert (row["season"], row["source_season"], row["game_type"]) == (2024, "2024", "R")
    assert row["game_date"] == "2024-04-01"
    assert row["kickoff_utc"] == "2024-04-02T02:10:00Z"
    assert row["kickoff_precision"] == "timestamp"
    assert row["home_team_name"] == "Los Angeles Dodgers"
    assert row["away_team_abbr"] == "NYY"
    assert row["winner_team_id"] == "119"
    assert row["outcome"] == "HOME_WIN"
    assert row["location"] == "Dodger Stadium" and row["neutral_site"] is False
    assert normalize_mlb_match(row) == row


def test_existing_ml_transform_output(game):
    from app.ml.features.download_multisport_data import normalize_mlb
    frame, _ = normalize_mlb(json.dumps({"dates": [{"games": [game]}]}).encode())
    row = normalize_mlb_match(frame.to_dict("records")[0], season=2024)
    assert row["home_team_id"] == "119"
    assert row["winner_team_id"] == "119"
    assert row["home_team_name"] is None and row["home_team_abbr"] is None
    assert row["kickoff_utc"] is None and row["kickoff_precision"] == "date"
    assert row["season"] == 2024
    # Actual exported files serialize calendar dates as UTC midnight.
    exported = io.StringIO(frame.to_csv(index=False))
    assert normalize_mlb_match(next(csv.DictReader(exported)), season=2024) == row


def test_away_win(game):
    game["teams"]["away"].update(score=8, isWinner=True)
    game["teams"]["home"]["isWinner"] = False
    row = normalize_mlb_match(game)
    assert row["outcome"] == "AWAY_WIN" and row["winner_team_id"] == "147"


@pytest.mark.parametrize("status,expected", [("Scheduled", "scheduled"), ("Suspended", "suspended"), ("In Progress", "in_progress"), ("Postponed", "postponed"), ("Cancelled", "cancelled")])
def test_nonfinal_ties_and_missing_scores(game, status, expected):
    game["status"]["detailedState"] = status
    for side in ("home", "away"):
        game["teams"][side].update(score=2, isWinner=False)
    row = normalize_mlb_match(game)
    assert row["status"] == expected and row["winner_team_id"] is None and row["outcome"] is None
    for side in ("home", "away"):
        game["teams"][side]["score"] = None
    assert normalize_mlb_match(game)["home_score"] is None


@pytest.mark.parametrize("status", ["Final", "Game Over", "Completed Early"])
def test_final_ties_rejected(game, status):
    game["status"]["detailedState"] = status
    game["teams"]["away"]["score"] = 5
    with pytest.raises(NormalizationError, match="tied"):
        normalize_mlb_match(game)


@pytest.mark.parametrize("field,value", [("officialDate", "bad"), ("officialDate", "2024-02-30"), ("gameDate", "bad"), ("gameDate", "2024-04-02T02:10:00"), ("gamePk", None), ("gamePk", []), ("season", "2023-24"), ("season", True), ("source", "")])
def test_invalid_top_level(game, field, value):
    game[field] = value
    with pytest.raises(NormalizationError):
        normalize_mlb_match(game)


@pytest.mark.parametrize("field,value", [("score", -1), ("score", "1.5"), ("score", None), ("score", float("nan")), ("score", True), ("isWinner", False)])
def test_invalid_result(game, field, value):
    game["teams"]["home"][field] = value
    with pytest.raises(NormalizationError):
        normalize_mlb_match(game)


def test_invalid_teams(game):
    for bad in (None, {}, {"id": "147"}):
        changed = deepcopy(game)
        changed["teams"]["home"]["team"] = bad
        with pytest.raises(NormalizationError):
            normalize_mlb_match(changed)


def test_duplicates_and_doubleheader(game):
    assert len(normalize_mlb_matches([game, game])) == 1
    assert len(normalize_matches([game, game])) == 1
    assert len(normalize_matches([game, dict(game, gamePk=745002)])) == 2
    assert len(normalize_matches([game, dict(game, source="another-provider")])) == 2
    conflict = deepcopy(game)
    conflict["teams"]["home"]["score"] = 6
    with pytest.raises(NormalizationError, match="Conflicting duplicate"):
        normalize_mlb_matches([game, conflict])


def test_offset_and_csv_roundtrip(game):
    game["gameDate"] = "2024-04-01T19:10:00-07:00"
    row = normalize_mlb_match(game)
    assert row["kickoff_utc"] == "2024-04-02T02:10:00Z"
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=MATCH_FIELDS)
    writer.writeheader()
    writer.writerow(row)
    buffer.seek(0)
    assert normalize_match_row(next(csv.DictReader(buffer))) == row


def test_inconsistent_canonical_result(game):
    row = normalize_mlb_match(game)
    with pytest.raises(NormalizationError, match="conflicts"):
        normalize_mlb_match(dict(row, winner_team_id="147"))
    with pytest.raises(NormalizationError, match="conflicts"):
        normalize_mlb_match(dict(row, outcome="DRAW"))


def test_mocked_ingestion(game):
    from backend.app.database.match_ingestion import upsert_match
    from backend.tests.test_match_ingestion import FakeConnection
    conn = FakeConnection()
    assert upsert_match(conn, normalize_mlb_match(game)) == 99
    league = next(params for sql, params in conn.calls if "SELECT id FROM leagues" in sql)
    assert league["name"] == "MLB"
    team = next(params for sql, params in conn.calls if "SELECT t.id FROM teams" in sql)
    assert team["sport_name"] == "BASEBALL"


def test_non_mapping():
    with pytest.raises(NormalizationError, match="mapping"):
        normalize_mlb_match(None)


def test_schedule_payload(game):
    payload = {"dates": [{"games": [game, game]}]}
    expected = normalize_mlb_matches([game])
    assert normalize_mlb_schedule(payload) == expected
    assert normalize_mlb_schedule(json.dumps(payload).encode()) == expected


@pytest.mark.parametrize("payload", [None, b"invalid", {}, {"dates": [{}]}, {"dates": [None]}])
def test_bad_schedule_payload(payload):
    with pytest.raises(NormalizationError, match="schedule payload"):
        normalize_mlb_schedule(payload)
