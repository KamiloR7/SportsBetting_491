from __future__ import annotations

import csv
from pathlib import Path

import pytest

from src.normalizers.multi_sport_normalizer import (
    MATCH_FIELDS,
    TEAM_FIELDS,
    NormalizationError,
    canonical_sport,
    canonical_status,
    normalize_files,
    normalize_match_row,
    normalize_matches,
    normalize_team_row,
    normalize_teams,
    validate_cross_references,
)


def uefa_team(team_id="86", abbr="RMA", name="Real Madrid CF"):
    return {
        "team_id": team_id,
        "sport": "SOCCER",
        "league": "UEFA Champions League",
        "team_abbr": abbr,
        "team_name": name,
        "conference": "Spain",
        "division": None,
        "country": "Spain",
        "venue": "Santiago Bernabeu",
        "founded": 1902,
        "source": "football-data.org/v4",
    }


def nfl_team(team_id="KC", abbr="KC", name="Kansas City Chiefs"):
    return {
        "team_id": team_id,
        "sport": "NFL",
        "league": "NFL",
        "team_abbr": abbr,
        "team_name": name,
        "conference": "AFC",
        "division": "West",
        "country": "USA",
        "venue": "Arrowhead Stadium",
        "founded": "1959",
        "source": "test-source",
    }


def uefa_match():
    return {
        "game_id": "1001",
        "sport": "SOCCER",
        "league": "UEFA Champions League",
        "season": 2026,
        "week": 1,
        "game_type": "REGULAR_SEASON",
        "game_date": "2026-09-16",
        "game_time_eastern": "15:00",
        "kickoff_utc": "2026-09-16T19:00:00+00:00",
        "home_team_id": "86",
        "home_team_abbr": "RMA",
        "home_team_name": "Real Madrid CF",
        "away_team_id": "65",
        "away_team_abbr": "MCI",
        "away_team_name": "Manchester City FC",
        "home_score": 2,
        "away_score": 1,
        "status": "completed",
        "winner_team_id": "86",
        "winner_team_abbr": "RMA",
        "location": "Santiago Bernabeu",
        "source": "football-data.org/v4",
    }


def nfl_match():
    return {
        "game_id": "1001",  # Same raw ID as UEFA on purpose.
        "sport": "NFL",
        "league": "NFL",
        "season": "2026",
        "week": "1",
        "game_type": "REG",
        "game_date": "2026-09-10",
        "game_time_eastern": "20:20",
        "kickoff_utc": "2026-09-11T00:20:00+00:00",
        "home_team_id": "KC",
        "home_team_abbr": "KC",
        "home_team_name": "Kansas City Chiefs",
        "away_team_id": "BUF",
        "away_team_abbr": "BUF",
        "away_team_name": "Buffalo Bills",
        "home_score": "27",
        "away_score": "24",
        "status": "FINAL",
        "winner_team_id": "",
        "winner_team_abbr": "",
        "location": "Arrowhead Stadium",
        "source": "test-source",
    }


def test_normalize_uefa_team_keeps_shared_shape():
    team = normalize_team_row(uefa_team())
    assert tuple(team.keys()) == TEAM_FIELDS
    assert team["sport"] == "SOCCER"
    assert team["team_id"] == "86"
    assert team["founded"] == 1902


def test_normalize_nfl_team_standardizes_sport_and_types():
    team = normalize_team_row(nfl_team())
    assert team["sport"] == "FOOTBALL"
    assert team["founded"] == 1959
    assert team["conference"] == "AFC"


def test_common_aliases_are_accepted_for_future_collectors():
    row = {
        "id": 7,
        "sport": "MLB",
        "competition": "MLB",
        "abbreviation": "LAD",
        "name": "Los Angeles Dodgers",
        "stadium": "Dodger Stadium",
        "data_source": "example",
    }
    team = normalize_team_row(row)
    assert team["team_id"] == "7"
    assert team["sport"] == "BASEBALL"
    assert team["venue"] == "Dodger Stadium"


def test_status_and_sport_aliases():
    assert canonical_sport("NFL") == "FOOTBALL"
    assert canonical_sport("EPL") == "SOCCER"
    assert canonical_sport("MLB") == "BASEBALL"
    assert canonical_status("FINAL") == "completed"
    assert canonical_status("TIMED") == "scheduled"
    assert canonical_status("IN_PLAY") == "in_progress"


def test_completed_match_derives_winner_and_converts_numeric_fields():
    match = normalize_match_row(nfl_match())
    assert tuple(match.keys()) == MATCH_FIELDS
    assert match["sport"] == "FOOTBALL"
    assert match["season"] == 2026
    assert match["week"] == 1
    assert match["home_score"] == 27
    assert match["winner_team_id"] == "KC"
    assert match["winner_team_abbr"] == "KC"


def test_completed_match_without_scores_is_rejected():
    row = nfl_match()
    row["home_score"] = ""
    with pytest.raises(NormalizationError, match="missing a final score"):
        normalize_match_row(row)


def test_same_source_id_is_allowed_across_different_sports():
    teams = normalize_teams([
        uefa_team("86", "RMA", "Real Madrid CF"),
        uefa_team("65", "MCI", "Manchester City FC"),
        nfl_team("KC", "KC", "Kansas City Chiefs"),
        nfl_team("BUF", "BUF", "Buffalo Bills"),
    ])
    matches = normalize_matches([uefa_match(), nfl_match()])

    checks = validate_cross_references(teams, matches)
    assert len(matches) == 2
    assert len(checks) == 5


def test_identical_duplicate_rows_are_collapsed():
    teams = normalize_teams([uefa_team(), uefa_team()])
    assert len(teams) == 1


def test_conflicting_duplicate_team_is_rejected():
    one = uefa_team()
    two = uefa_team()
    two["team_name"] = "Different Name"
    with pytest.raises(NormalizationError, match="Conflicting duplicate team_id"):
        normalize_teams([one, two])


def test_unknown_team_reference_is_rejected():
    teams = normalize_teams([
        uefa_team("86", "RMA", "Real Madrid CF"),
        uefa_team("65", "MCI", "Manchester City FC"),
    ])
    match = uefa_match()
    match["away_team_id"] = "999"
    matches = normalize_matches([match])

    with pytest.raises(NormalizationError, match="unknown away team"):
        validate_cross_references(teams, matches)


def test_normalize_files_writes_canonical_csvs(tmp_path: Path):
    team_input = tmp_path / "teams_in.csv"
    match_input = tmp_path / "matches_in.csv"

    team_rows = [
        uefa_team("86", "RMA", "Real Madrid CF"),
        uefa_team("65", "MCI", "Manchester City FC"),
    ]
    match_rows = [uefa_match()]

    with team_input.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TEAM_FIELDS)
        writer.writeheader()
        writer.writerows(team_rows)

    with match_input.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MATCH_FIELDS)
        writer.writeheader()
        writer.writerows(match_rows)

    teams_path, matches_path, checks = normalize_files(
        [team_input], [match_input], tmp_path / "normalized"
    )

    assert teams_path.exists()
    assert matches_path.exists()
    assert len(checks) == 5

    with teams_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["team_abbr"] == "RMA"
