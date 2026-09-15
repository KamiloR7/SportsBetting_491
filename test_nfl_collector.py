from __future__ import annotations

import csv
from pathlib import Path

import pytest

from src.collectors.nfl_collector import (
    CollectorResult,
    NFLCollector,
    NFLCollectorError,
    normalize_game,
    normalize_team,
    validate_result,
    write_csv,
)


def make_teams():
    abbreviations = [
        "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
        "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
        "LV", "LAC", "LA", "MIA", "MIN", "NE", "NO", "NYG",
        "NYJ", "PHI", "PIT", "SF", "SEA", "TB", "TEN", "WAS",
    ]
    return [
        {
            "team_abbr": abbr,
            "team_name": f"{abbr} Test Team",
            "team_id": f"ID-{abbr}",
            "team_conf": "AFC" if i % 2 == 0 else "NFC",
            "team_division": "Test Division",
        }
        for i, abbr in enumerate(abbreviations)
    ]


def make_games():
    return [
        {
            "game_id": "2025_01_BUF_BAL",
            "season": 2025,
            "game_type": "REG",
            "week": 1,
            "gameday": "2025-09-07",
            "gametime": "20:20",
            "away_team": "BUF",
            "away_score": 30,
            "home_team": "BAL",
            "home_score": 27,
            "location": "Home",
        },
        {
            "game_id": "2025_02_KC_PHI",
            "season": 2025,
            "game_type": "REG",
            "week": 2,
            "gameday": "2025-09-14",
            "gametime": "16:25",
            "away_team": "KC",
            "away_score": None,
            "home_team": "PHI",
            "home_score": None,
            "location": "Home",
        },
    ]


def test_normalize_team():
    row = make_teams()[0]
    team = normalize_team(row)
    assert team["team_id"] == "ID-ARI"
    assert team["team_abbr"] == "ARI"
    assert team["sport"] == "NFL"


def test_completed_away_winner_and_utc_timestamp():
    teams = {t["team_abbr"]: normalize_team(t) for t in make_teams()}
    game = normalize_game(make_games()[0], teams)
    assert game["status"] == "completed"
    assert game["winner_team_abbr"] == "BUF"
    assert game["winner_team_id"] == "ID-BUF"
    assert game["kickoff_utc"] == "2025-09-08T00:20:00+00:00"


def test_scheduled_game_has_no_winner():
    teams = {t["team_abbr"]: normalize_team(t) for t in make_teams()}
    game = normalize_game(make_games()[1], teams)
    assert game["status"] == "scheduled"
    assert game["winner_team_id"] is None
    assert game["home_score"] is None


def test_tie_game():
    teams = {t["team_abbr"]: normalize_team(t) for t in make_teams()}
    row = dict(make_games()[0], away_score=20, home_score=20)
    game = normalize_game(row, teams)
    assert game["status"] == "completed"
    assert game["winner_team_abbr"] == "TIE"
    assert game["winner_team_id"] is None


def test_collector_injected_loaders_and_validation():
    collector = NFLCollector(team_loader=make_teams, schedule_loader=lambda season: make_games())
    result = collector.collect(2025)
    checks = validate_result(result)
    assert len(result.teams) == 32
    assert len(result.games) == 2
    assert len(checks) == 5


def test_write_csv(tmp_path: Path):
    output = write_csv([normalize_team(make_teams()[0])], tmp_path / "teams.csv")
    with output.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["team_abbr"] == "ARI"


def test_error_on_bad_team_row():
    with pytest.raises(NFLCollectorError):
        normalize_team({"team_abbr": "BUF"})


def test_error_on_empty_dataset_write(tmp_path: Path):
    with pytest.raises(NFLCollectorError):
        write_csv([], tmp_path / "empty.csv")
