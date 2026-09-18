from __future__ import annotations

import csv
from pathlib import Path

import pytest

from uefa_collector import (
    CollectorResult,
    UEFACollector,
    UEFACollectorError,
    normalize_game,
    normalize_team,
    validate_result,
    write_csv,
)


def make_teams_payload():
    return {
        "competition": {"id": 2001, "name": "UEFA Champions League", "code": "CL"},
        "season": {"startDate": "2026-07-01"},
        "teams": [
            {
                "id": 86,
                "name": "Real Madrid CF",
                "shortName": "Real Madrid",
                "tla": "RMA",
                "area": {"name": "Spain"},
                "venue": "Santiago Bernabeu",
                "founded": 1902,
            },
            {
                "id": 65,
                "name": "Manchester City FC",
                "shortName": "Man City",
                "tla": "MCI",
                "area": {"name": "England"},
                "venue": "Etihad Stadium",
                "founded": 1880,
            },
        ],
    }


def make_matches_payload():
    return {
        "competition": {"id": 2001, "name": "UEFA Champions League", "code": "CL"},
        "matches": [
            {
                "id": 1001,
                "utcDate": "2026-09-16T19:00:00Z",
                "status": "FINISHED",
                "matchday": 1,
                "stage": "REGULAR_SEASON",
                "season": {"startDate": "2026-07-01"},
                "homeTeam": {"id": 86, "name": "Real Madrid CF", "tla": "RMA"},
                "awayTeam": {"id": 65, "name": "Manchester City FC", "tla": "MCI"},
                "score": {"fullTime": {"home": 2, "away": 1}},
                "venue": "Santiago Bernabeu",
            },
            {
                "id": 1002,
                "utcDate": "2026-10-01T19:00:00Z",
                "status": "TIMED",
                "matchday": 2,
                "stage": "REGULAR_SEASON",
                "season": {"startDate": "2026-07-01"},
                "homeTeam": {"id": 65, "name": "Manchester City FC", "tla": "MCI"},
                "awayTeam": {"id": 86, "name": "Real Madrid CF", "tla": "RMA"},
                "score": {"fullTime": {"home": None, "away": None}},
                "venue": "Etihad Stadium",
            },
        ],
    }


def normalized_teams_by_id():
    return {
        str(team["id"]): normalize_team(team)
        for team in make_teams_payload()["teams"]
    }


def test_normalize_team():
    team = normalize_team(make_teams_payload()["teams"][0])

    assert team["team_id"] == "86"
    assert team["team_abbr"] == "RMA"
    assert team["team_name"] == "Real Madrid CF"
    assert team["sport"] == "SOCCER"
    assert team["league"] == "UEFA Champions League"
    assert team["country"] == "Spain"


def test_completed_home_winner_and_utc_timestamp():
    game = normalize_game(make_matches_payload()["matches"][0], normalized_teams_by_id())

    assert game["status"] == "completed"
    assert game["winner_team_abbr"] == "RMA"
    assert game["winner_team_id"] == "86"
    assert game["kickoff_utc"] == "2026-09-16T19:00:00+00:00"
    assert game["game_time_eastern"] == "15:00"
    assert game["home_score"] == 2
    assert game["away_score"] == 1


def test_scheduled_game_has_no_winner():
    game = normalize_game(make_matches_payload()["matches"][1], normalized_teams_by_id())

    assert game["status"] == "scheduled"
    assert game["winner_team_id"] is None
    assert game["winner_team_abbr"] is None
    assert game["home_score"] is None


def test_tie_game():
    row = dict(make_matches_payload()["matches"][0])
    row["score"] = {"fullTime": {"home": 1, "away": 1}}
    game = normalize_game(row, normalized_teams_by_id())

    assert game["status"] == "completed"
    assert game["winner_team_abbr"] == "TIE"
    assert game["winner_team_id"] is None


def test_collector_injected_loaders_and_validation():
    collector = UEFACollector(
        team_loader=lambda season: make_teams_payload(),
        match_loader=lambda season: make_matches_payload(),
    )

    result = collector.collect(2026)
    checks = validate_result(result)

    assert len(result.teams) == 2
    assert len(result.games) == 2
    assert len(checks) == 5


def test_write_csv(tmp_path: Path):
    output = write_csv(
        [normalize_team(make_teams_payload()["teams"][0])],
        tmp_path / "teams.csv",
    )

    with output.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert rows[0]["team_abbr"] == "RMA"


def test_error_on_bad_team_row():
    with pytest.raises(UEFACollectorError):
        normalize_team({"id": 86})


def test_error_on_bad_match_row():
    with pytest.raises(UEFACollectorError):
        normalize_game({"id": 10}, normalized_teams_by_id())


def test_error_on_empty_dataset_write(tmp_path: Path):
    with pytest.raises(UEFACollectorError):
        write_csv([], tmp_path / "empty.csv")


def test_missing_token_error():
    collector = UEFACollector(api_token=None)
    collector.api_token = None
    with pytest.raises(UEFACollectorError, match="FOOTBALL_DATA_API_TOKEN"):
        collector._request_json("/competitions/CL/teams", {"season": 2026})


def test_validation_rejects_unknown_team_reference():
    teams = [normalize_team(team) for team in make_teams_payload()["teams"]]
    games = [normalize_game(make_matches_payload()["matches"][0], normalized_teams_by_id())]
    games[0]["away_team_id"] = "999"

    with pytest.raises(UEFACollectorError, match="team not found"):
        validate_result(CollectorResult(teams=teams, games=games))
