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


def run_seed() -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)

    with engine.begin() as conn:
        nfl = _league_id(conn, "NFL")
        mlb = _league_id(conn, "MLB")
        epl = _league_id(conn, "EPL")

        match_specs = [
            (nfl, "american-football", "KC", "PHI", now + timedelta(days=3), "scheduled", None, None),
            (nfl, "american-football", "DAL", "SF", now - timedelta(days=12), "final", 21, 28),
            (mlb, "baseball", "NYY", "LAD", now + timedelta(days=4), "scheduled", None, None),
            (mlb, "baseball", "BOS", "CHC", now - timedelta(days=10), "final", 5, 3),
            (epl, "soccer", "MCI", "ARS", now + timedelta(days=5), "scheduled", None, None),
            (epl, "soccer", "LIV", "CHE", now - timedelta(days=9), "final", 2, 1),
        ]

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
