"""
Development match seed data for the Sprint 3 match-prediction UI.

Run after loading the schema and base seed data:
    python -m app.database.seed_data
    python -m app.database.seed_dev_matches
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.database.db import engine


def _league_id(conn, abbreviation: str) -> int:
    row = conn.execute(
        text("SELECT id FROM leagues WHERE abbreviation = :abbreviation"),
        {"abbreviation": abbreviation},
    ).first()

    if row is None:
        raise RuntimeError(f"League not found: {abbreviation}")

    return row.id


def _team_id(conn, abbreviation: str, sport_slug: str) -> int:
    row = conn.execute(
        text(
            """
            SELECT t.id
            FROM teams t
            JOIN sports s ON s.id = t.sport_id
            WHERE t.abbreviation = :abbreviation
              AND s.slug = :sport_slug
            """
        ),
        {
            "abbreviation": abbreviation,
            "sport_slug": sport_slug,
        },
    ).first()

    if row is None:
        raise RuntimeError(f"Team not found: {sport_slug} {abbreviation}")

    return row.id


def _insert_match(
    conn,
    *,
    league_id: int,
    home_team_id: int,
    away_team_id: int,
    start_time: datetime,
    status: str,
    home_score: int | None = None,
    away_score: int | None = None,
) -> None:
    existing = conn.execute(
        text(
            """
            SELECT id
            FROM matches
            WHERE league_id = :league_id
              AND home_team_id = :home_team_id
              AND away_team_id = :away_team_id
              AND start_time = :start_time
            """
        ),
        {
            "league_id": league_id,
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "start_time": start_time,
        },
    ).first()

    if existing:
        return

    conn.execute(
        text(
            """
            INSERT INTO matches (
                league_id,
                home_team_id,
                away_team_id,
                start_time,
                status,
                home_score,
                away_score
            )
            VALUES (
                :league_id,
                :home_team_id,
                :away_team_id,
                :start_time,
                :status,
                :home_score,
                :away_score
            )
            """
        ),
        {
            "league_id": league_id,
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "start_time": start_time,
            "status": status,
            "home_score": home_score,
            "away_score": away_score,
        },
    )


def run_seed(db_engine=engine) -> None:
    now = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)

    with db_engine.begin() as conn:
        nfl = _league_id(conn, "NFL")
        mlb = _league_id(conn, "MLB")
        epl = _league_id(conn, "EPL")

        # Sample development results only; these are not current league schedules.
        sport_samples = [
            (nfl, "american-football", ["KC", "PHI", "DAL", "SF", "BUF", "GB"],
             [(28, 17), (17, 24), (14, 31), (35, 20), (24, 27), (30, 21)]),
            (mlb, "baseball", ["NYY", "LAD", "BOS", "CHC", "HOU", "ATL"],
             [(6, 3), (2, 5), (3, 4), (7, 2), (1, 5), (5, 4)]),
            (epl, "soccer", ["MCI", "ARS", "LIV", "CHE", "MUN", "TOT"],
             [(2, 1), (0, 2), (1, 1), (3, 0), (0, 0), (1, 2)]),
        ]
        match_specs = [
            (nfl, "american-football", "KC", "PHI", now + timedelta(days=3), "scheduled", None, None),
            (mlb, "baseball", "NYY", "LAD", now + timedelta(days=4), "scheduled", None, None),
            (epl, "soccer", "MCI", "ARS", now + timedelta(days=5), "scheduled", None, None),
        ]
        for league_id, sport_slug, teams, scores in sport_samples:
            for index in range(18):
                home_score, away_score = scores[index % len(scores)]
                match_specs.append((
                    league_id, sport_slug, teams[index % len(teams)],
                    teams[(index + 3) % len(teams)],
                    now - timedelta(days=30 - index), "final", home_score, away_score,
                ))

        for league_id, sport_slug, home, away, start_time, status, home_score, away_score in match_specs:
            _insert_match(
                conn,
                league_id=league_id,
                home_team_id=_team_id(conn, home, sport_slug),
                away_team_id=_team_id(conn, away, sport_slug),
                start_time=start_time,
                status=status,
                home_score=home_score,
                away_score=away_score,
            )


if __name__ == "__main__":
    run_seed()
    print("Development matches applied.")
