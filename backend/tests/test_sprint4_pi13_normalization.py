"""Sprint 4 PI1.3 deterministic normalization acceptance fixtures."""

from __future__ import annotations

import pytest

from src.normalizers.multi_sport_normalizer import (
    MATCH_FIELDS,
    NormalizationError,
    normalize_match_row,
    normalize_matches,
)


def expected_match(**overrides):
    """Build a complete expected canonical record without using the normalizer."""
    expected = dict.fromkeys(MATCH_FIELDS)
    expected.update(overrides)
    return expected


def mlb_game(game_id, official_date, detailed_state, home_score=None, away_score=None):
    home = {"team": {"id": 111, "name": "Home Club", "abbreviation": "HOM"}}
    away = {"team": {"id": 222, "name": "Away Club", "abbreviation": "AWY"}}
    if home_score is not None:
        home.update(score=home_score, isWinner=home_score > away_score)
    if away_score is not None:
        away.update(score=away_score, isWinner=away_score > home_score)
    return {
        "gamePk": game_id,
        "officialDate": official_date,
        "gameDate": f"{official_date}T19:10:00Z",
        "gameType": "R",
        "status": {"detailedState": detailed_state},
        "teams": {"home": home, "away": away},
        "venue": {"name": "Central Park"},
    }


NFL_FIXTURES = [
    (
        {
            "game_id": "nfl-home-win",
            "sport": "NFL",
            "league": "NFL",
            "season": "2025",
            "week": "9",
            "game_date": "2025-11-02",
            "game_time_eastern": "13:00",
            "kickoff_utc": "2025-11-02T18:00:00Z",
            "home_team_id": "KC",
            "home_team_abbr": "KC",
            "home_team_name": "Kansas City Chiefs",
            "away_team_id": "BUF",
            "away_team_abbr": "BUF",
            "away_team_name": "Buffalo Bills",
            "home_score": 24,
            "away_score": 17,
            "status": "FINAL",
            "source": "fixture.nfl",
        },
        expected_match(
            game_id="nfl-home-win", sport="American Football", league="NFL",
            season=2025, week=9, game_date="2025-11-02",
            game_time_eastern="13:00", kickoff_utc="2025-11-02T18:00:00Z",
            home_team_id="KC", home_team_abbr="KC", home_team_name="Kansas City Chiefs",
            away_team_id="BUF", away_team_abbr="BUF", away_team_name="Buffalo Bills",
            home_score=24, away_score=17, status="completed", winner_team_id="KC",
            winner_team_abbr="KC", source="fixture.nfl",
        ),
    ),
    (
        {
            "game_id": "nfl-scheduled",
            "sport": "American Football",
            "league": "NFL",
            "season": 2025,
            "week": 10,
            "game_date": "2025-11-09",
            "game_time_eastern": "16:25",
            "home_team_id": "DAL",
            "home_team_abbr": "DAL",
            "home_team_name": "Dallas Cowboys",
            "away_team_id": "PHI",
            "away_team_abbr": "PHI",
            "away_team_name": "Philadelphia Eagles",
            "status": "SCHEDULED",
            "source": "fixture.nfl",
        },
        expected_match(
            game_id="nfl-scheduled", sport="American Football", league="NFL",
            season=2025, week=10, game_date="2025-11-09",
            game_time_eastern="16:25", kickoff_utc="2025-11-09T21:25:00Z",
            home_team_id="DAL", home_team_abbr="DAL", home_team_name="Dallas Cowboys",
            away_team_id="PHI", away_team_abbr="PHI", away_team_name="Philadelphia Eagles",
            status="scheduled", source="fixture.nfl",
        ),
    ),
    (
        {
            "game_id": "nfl-tie",
            "sport": "American Football",
            "league": "NFL",
            "season": 2024,
            "week": 4,
            "game_date": "2024-09-29",
            "game_time_eastern": "13:00",
            "home_team_id": "PIT",
            "home_team_abbr": "PIT",
            "home_team_name": "Pittsburgh Steelers",
            "away_team_id": "IND",
            "away_team_abbr": "IND",
            "away_team_name": "Indianapolis Colts",
            "home_score": 20,
            "away_score": 20,
            "status": "FINAL",
            "source": "fixture.nfl",
        },
        expected_match(
            game_id="nfl-tie", sport="American Football", league="NFL",
            season=2024, week=4, game_date="2024-09-29",
            game_time_eastern="13:00", kickoff_utc="2024-09-29T17:00:00Z",
            home_team_id="PIT", home_team_abbr="PIT", home_team_name="Pittsburgh Steelers",
            away_team_id="IND", away_team_abbr="IND", away_team_name="Indianapolis Colts",
            home_score=20, away_score=20, status="completed", winner_team_abbr="TIE",
            source="fixture.nfl",
        ),
    ),
]

MLB_FIXTURES = [
    (
        mlb_game(812001, "2025-06-14", "Final", 5, 3),
        expected_match(
            game_id="812001", sport="BASEBALL", league="MLB", season=2025,
            game_date="2025-06-14", kickoff_utc="2025-06-14T19:10:00Z",
            home_team_id="111", home_team_abbr="HOM", home_team_name="Home Club",
            away_team_id="222", away_team_abbr="AWY", away_team_name="Away Club",
            home_score=5, away_score=3, status="completed", winner_team_id="111",
            winner_team_abbr="HOM", game_type="R", location="Central Park",
            source="statsapi.mlb.com", outcome="HOME_WIN", source_season="2025",
            kickoff_precision="timestamp",
        ),
    ),
    (
        mlb_game(812002, "2025-06-15", "Scheduled"),
        expected_match(
            game_id="812002", sport="BASEBALL", league="MLB", season=2025,
            game_date="2025-06-15", kickoff_utc="2025-06-15T19:10:00Z",
            home_team_id="111", home_team_abbr="HOM", home_team_name="Home Club",
            away_team_id="222", away_team_abbr="AWY", away_team_name="Away Club",
            status="scheduled", game_type="R", location="Central Park",
            source="statsapi.mlb.com", source_season="2025",
            kickoff_precision="timestamp",
        ),
    ),
    (
        {
            **mlb_game(812003, "2025-06-16", "Postponed"),
            "gameDate": None,
        },
        expected_match(
            game_id="812003", sport="BASEBALL", league="MLB", season=2025,
            game_date="2025-06-16", home_team_id="111", home_team_abbr="HOM",
            home_team_name="Home Club", away_team_id="222", away_team_abbr="AWY",
            away_team_name="Away Club", status="postponed", game_type="R",
            location="Central Park", source="statsapi.mlb.com",
            source_season="2025", kickoff_precision="date",
        ),
    ),
]

EPL_FIXTURES = [
    (
        {
            "game_id": "epl-home-win", "sport": "SOCCER", "league": "PL",
            "source": "football-data.org/v4", "season": "2025-2026",
            "game_date": "2025-09-01", "kickoff_utc": "2025-09-01T19:00:00+00:00",
            "home_team_id": "ars", "home_team_name": "Arsenal",
            "away_team_id": "lee", "away_team_name": "Leeds United",
            "home_score": 2, "away_score": 0, "status": "FINISHED",
        },
        expected_match(
            game_id="epl-home-win", sport="SOCCER", league="EPL", season=2025,
            game_date="2025-09-01", kickoff_utc="2025-09-01T19:00:00Z",
            home_team_id="ars", home_team_name="Arsenal", away_team_id="lee",
            away_team_name="Leeds United", home_score=2, away_score=0,
            status="completed", winner_team_id="ars", outcome="HOME_WIN",
            source="football-data.org/v4", source_season="2025-2026",
            kickoff_precision="timestamp",
        ),
    ),
    (
        {
            "game_id": "epl-draw", "sport": "SOCCER", "league": "EPL",
            "source": "football-data.org/v4", "season": "2025-2026",
            "game_date": "2025-09-02", "kickoff_utc": "2025-09-02T18:30:00Z",
            "home_team_id": "ful", "home_team_name": "Fulham",
            "away_team_id": "bre", "away_team_name": "Brentford",
            "home_score": 1, "away_score": 1, "status": "FINISHED",
        },
        expected_match(
            game_id="epl-draw", sport="SOCCER", league="EPL", season=2025,
            game_date="2025-09-02", kickoff_utc="2025-09-02T18:30:00Z",
            home_team_id="ful", home_team_name="Fulham", away_team_id="bre",
            away_team_name="Brentford", home_score=1, away_score=1,
            status="completed", winner_team_abbr="DRAW", outcome="DRAW",
            source="football-data.org/v4", source_season="2025-2026",
            kickoff_precision="timestamp",
        ),
    ),
    (
        {
            "game_id": "epl-scheduled", "sport": "SOCCER", "league": "PL",
            "source": "football-data.org/v4", "season": "2025-2026",
            "game_date": "2026-02-01", "kickoff_utc": "2026-02-01T17:30:00Z",
            "home_team_id": "liv", "home_team_name": "Liverpool",
            "away_team_id": "mci", "away_team_name": "Manchester City",
            "status": "TIMED",
        },
        expected_match(
            game_id="epl-scheduled", sport="SOCCER", league="EPL", season=2025,
            game_date="2026-02-01", kickoff_utc="2026-02-01T17:30:00Z",
            home_team_id="liv", home_team_name="Liverpool", away_team_id="mci",
            away_team_name="Manchester City", status="scheduled",
            source="football-data.org/v4", source_season="2025-2026",
            kickoff_precision="timestamp",
        ),
    ),
]


@pytest.mark.parametrize(
    ("raw_match", "expected"),
    NFL_FIXTURES + MLB_FIXTURES + EPL_FIXTURES,
    ids=["nfl-home-win", "nfl-scheduled", "nfl-tie", "mlb-home-win", "mlb-scheduled", "mlb-postponed", "epl-home-win", "epl-draw", "epl-scheduled"],
)
def test_sprint4_pi13_matches_exact_canonical_output(raw_match, expected):
    actual = normalize_match_row(raw_match)

    assert tuple(actual) == MATCH_FIELDS
    assert actual == expected


INVALID_MATCHES = [
    pytest.param(
        {
            "game_id": "bad-nfl", "sport": "NFL", "league": "NFL",
            "season": 2025, "week": 1, "game_date": "2025-09-07",
            "home_team_id": "KC", "home_team_abbr": "KC",
            "away_team_id": "KC", "away_team_abbr": "KC",
            "status": "SCHEDULED", "source": "fixture.nfl",
        },
        "teams must differ",
        id="nfl-identical-teams",
    ),
    pytest.param(
        {
            "gamePk": 812004, "officialDate": "2025-06-17",
            "gameDate": "2025-06-17T19:10:00", "status": {"detailedState": "Scheduled"},
            "teams": {
                "home": {"team": {"id": 111}},
                "away": {"team": {"id": 222}},
            },
        },
        "timezone required",
        id="mlb-naive-kickoff",
    ),
    pytest.param(
        {
            "game_id": "bad-epl", "sport": "SOCCER", "league": "PL",
            "source": "football-data.org/v4", "season": "2025-2026",
            "game_date": "2025-09-03", "home_team_id": "ful",
            "home_team_name": "Fulham", "away_team_id": "bre",
            "away_team_name": "Brentford", "home_score": 2, "away_score": 0,
            "status": "FINISHED", "FTR": "A",
        },
        "FTR conflicts",
        id="epl-conflicting-result",
    ),
]


@pytest.mark.parametrize(("raw_match", "error"), INVALID_MATCHES)
def test_invalid_records_are_rejected_before_ingestion(raw_match, error):
    with pytest.raises(NormalizationError, match=error):
        normalize_matches([raw_match])
