from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from sqlalchemy import text


STATUS_MAP = {
    "scheduled": "scheduled",
    "in_progress": "in_progress",
    "completed": "final",
    "postponed": "postponed",
    "cancelled": "cancelled",
}


def _resolve_league_id(conn, league_name: str) -> int:
    row = conn.execute(
        text(
            """
            SELECT id
            FROM leagues
            WHERE name = :name OR abbreviation = :name
            LIMIT 1
            """
        ),
        {"name": league_name},
    ).first()

    if row is None:
        raise ValueError(f"League not found: {league_name}")

    return row.id


def _resolve_team_id(
    conn,
    *,
    sport_name: str,
    team_name: str | None,
    team_abbr: str | None,
) -> int:
    row = conn.execute(
        text(
            """
            SELECT t.id
            FROM teams t
            JOIN sports s ON s.id = t.sport_id
            WHERE
                (
                    (:team_name IS NOT NULL AND t.name = :team_name)
                    OR
                    (:team_abbr IS NOT NULL AND t.abbreviation = :team_abbr)
                )
                AND (
                    UPPER(s.name) = UPPER(:sport_name)
                    OR UPPER(s.slug) = UPPER(:sport_name)
                )
            LIMIT 1
            """
        ),
        {
            "team_name": team_name,
            "team_abbr": team_abbr,
            "sport_name": sport_name,
        },
    ).first()

    if row is None:
        raise ValueError(
            f"Team not found for sport={sport_name}, "
            f"name={team_name}, abbr={team_abbr}"
        )

    return row.id


def _resolve_data_source_id(conn, source_name: str) -> int:
    conn.execute(
        text(
            """
            INSERT INTO data_sources (name, source_type)
            VALUES (:name, 'api')
            ON CONFLICT (name) DO NOTHING
            """
        ),
        {"name": source_name},
    )

    row = conn.execute(
        text("SELECT id FROM data_sources WHERE name = :name"),
        {"name": source_name},
    ).first()

    if row is None:
        raise ValueError(f"Data source could not be resolved: {source_name}")

    return row.id


def _resolve_existing_match_id(
    conn,
    *,
    data_source_id: int,
    external_id: str,
) -> int | None:
    row = conn.execute(
        text(
            """
            SELECT entity_id
            FROM external_mappings
            WHERE data_source_id = :data_source_id
              AND entity_type = 'match'
              AND external_id = :external_id
            """
        ),
        {
            "data_source_id": data_source_id,
            "external_id": external_id,
        },
    ).first()

    return row.entity_id if row else None


def upsert_match(conn, match: Mapping[str, Any]) -> int:
    game_id = str(match["game_id"])
    source_name = str(match.get("source") or "unknown")

    sport_name = str(match["sport"])
    league_name = str(match["league"])

    league_id = _resolve_league_id(conn, league_name)

    home_team_id = _resolve_team_id(
        conn,
        sport_name=sport_name,
        team_name=match.get("home_team_name"),
        team_abbr=match.get("home_team_abbr"),
    )

    away_team_id = _resolve_team_id(
        conn,
        sport_name=sport_name,
        team_name=match.get("away_team_name"),
        team_abbr=match.get("away_team_abbr"),
    )

    data_source_id = _resolve_data_source_id(conn, source_name)

    db_status = STATUS_MAP.get(str(match["status"]))
    if db_status is None:
        raise ValueError(f"Unsupported match status: {match['status']}")

    kickoff_utc = match.get("kickoff_utc")
    if not kickoff_utc:
        raise ValueError(f"Match {game_id} is missing kickoff_utc")

    existing_match_id = _resolve_existing_match_id(
        conn,
        data_source_id=data_source_id,
        external_id=game_id,
    )

    if existing_match_id is not None:
        conn.execute(
            text(
                """
                UPDATE matches
                SET
                    league_id = :league_id,
                    home_team_id = :home_team_id,
                    away_team_id = :away_team_id,
                    start_time = :start_time,
                    status = :status,
                    home_score = :home_score,
                    away_score = :away_score,
                    updated_at = NOW()
                WHERE id = :match_id
                """
            ),
            {
                "match_id": existing_match_id,
                "league_id": league_id,
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "start_time": kickoff_utc,
                "status": db_status,
                "home_score": match.get("home_score"),
                "away_score": match.get("away_score"),
            },
        )

        return existing_match_id

    row = conn.execute(
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
            RETURNING id
            """
        ),
        {
            "league_id": league_id,
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "start_time": kickoff_utc,
            "status": db_status,
            "home_score": match.get("home_score"),
            "away_score": match.get("away_score"),
        },
    ).first()

    match_id = row.id

    conn.execute(
        text(
            """
            INSERT INTO external_mappings (
                data_source_id,
                entity_type,
                entity_id,
                external_id
            )
            VALUES (
                :data_source_id,
                'match',
                :entity_id,
                :external_id
            )
            """
        ),
        {
            "data_source_id": data_source_id,
            "entity_id": match_id,
            "external_id": game_id,
        },
    )

    return match_id