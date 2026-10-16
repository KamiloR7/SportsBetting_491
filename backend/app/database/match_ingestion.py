"""PostgreSQL match writes. Call inside a caller-owned transaction.

Historical importers must use historical_import.load_historical_matches(),
which serializes cooperating importers and runs DATA-24 validation first.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Mapping

from sqlalchemy import text

logger = logging.getLogger(__name__)
STATUS_MAP = {"scheduled": "scheduled", "in_progress": "in_progress",
              "completed": "final", "postponed": "postponed", "cancelled": "cancelled"}


class ReferenceResolutionError(ValueError):
    """A required reference is missing, ambiguous or inconsistent."""


class MatchIdentityError(ValueError):
    """A stored source mapping is dangling or changes match identity."""


def _one(result, description):
    rows = result.all()
    if len(rows) != 1:
        raise ReferenceResolutionError(f"{description}: expected one reference, found {len(rows)}")
    return rows[0]


def _existing_source_id(conn, source):
    row = conn.execute(text("SELECT id FROM data_sources WHERE name = :name"), {"name": source}).first()
    return row.id if row else None


def _resolve_team_id(conn, *, sport_id, sport_name, team_name, team_abbr, external_id, source_id):
    if external_id is not None and source_id is not None:
        mapped = conn.execute(text("""SELECT entity_id FROM external_mappings
            WHERE data_source_id = :source_id AND entity_type = 'team'
              AND external_id = :external_id"""),
            {"source_id": source_id, "external_id": str(external_id)}).first()
        if mapped:
            return _one(conn.execute(text("""SELECT t.id FROM teams t
                WHERE t.id = :team_id AND t.sport_id = :sport_id"""),
                {"team_id": mapped.entity_id, "sport_id": sport_id}),
                f"Mapped team {external_id} (missing target or wrong sport)").id
    return _one(conn.execute(text("""SELECT t.id FROM teams t
        WHERE t.sport_id = :sport_id AND
        ((:team_name IS NOT NULL AND t.name = :team_name) OR
         (:team_abbr IS NOT NULL AND t.abbreviation = :team_abbr))"""),
        {"sport_id": sport_id, "sport_name": sport_name,
         "team_name": team_name, "team_abbr": team_abbr}),
        f"Team name={team_name}, abbreviation={team_abbr}; provide an external mapping if unresolved").id


def resolve_match_references(conn, match: Mapping[str, Any], *, require_season=False):
    """Resolve existing records only. Provider IDs never become internal IDs.

    Explicit team mappings are authoritative over provider display names.
    Fallback exact-name/abbreviation matches must be unique within the sport.
    No missing sport, league, team, or season is created.
    """
    sport_name = str(match["sport"])
    sport = _one(conn.execute(text("""SELECT id FROM sports
        WHERE UPPER(name) = UPPER(:name) OR UPPER(slug) = UPPER(:name)"""),
        {"name": sport_name}), f"Sport {sport_name}")
    league = _one(conn.execute(text("""SELECT id FROM leagues
        WHERE sport_id = :sport_id AND (name = :name OR abbreviation = :name)"""),
        {"sport_id": sport.id, "name": match["league"]}), f"League {match['league']}")
    source_id = _existing_source_id(conn, match["source"])
    teams = {}
    for side in ("home", "away"):
        teams[side] = _resolve_team_id(conn, sport_id=sport.id, sport_name=sport_name,
            team_name=match.get(f"{side}_team_name"), team_abbr=match.get(f"{side}_team_abbr"),
            external_id=match.get(f"{side}_team_id"), source_id=source_id)
    if teams["home"] == teams["away"]:
        raise ReferenceResolutionError("Home and away resolve to the same database team")
    season_id = None
    year = match.get("season")
    if year is None and require_season:
        raise ReferenceResolutionError("Missing season")
    if year is not None:
        year = int(year)
        label = f"{year}-{str(year + 1)[-2:]}" if match["league"] == "EPL" else str(year)
        season_id = _one(conn.execute(text("""SELECT id FROM seasons
            WHERE league_id = :league_id AND name = :name"""),
            {"league_id": league.id, "name": label}), f"Season {label} for league {league.id}").id
    return {"league_id": league.id, "home_team_id": teams["home"],
            "away_team_id": teams["away"], "season_id": season_id}


def upsert_match(conn, match: Mapping[str, Any], *, references=None, return_action=False):
    """Insert/update within the caller's transaction; default result is match ID.

    Optional references are the result of resolve_match_references on this
    connection. return_action adds inserted/updated for batch accounting.
    """
    if not conn.in_transaction():
        raise ValueError("upsert_match requires an active transaction")
    game_id = str(match["game_id"])
    source = match.get("source")
    if not source:
        raise ValueError("Match is missing source")
    status = STATUS_MAP.get(str(match["status"]))
    if status is None:
        raise ValueError(f"Unsupported match status: {match['status']}")
    kickoff = match.get("kickoff_utc")
    try:
        kickoff = datetime.fromisoformat(str(kickoff).replace("Z", "+00:00"))
        if kickoff.tzinfo is None or kickoff.utcoffset() is None:
            raise ValueError
        kickoff = kickoff.astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise ValueError("Match requires valid timezone-aware kickoff_utc") from exc
    refs = references if references is not None else resolve_match_references(conn, match)
    conn.execute(text("""INSERT INTO data_sources (name, source_type) VALUES (:name, :source_type)
        ON CONFLICT (name) DO NOTHING"""),
        {"name": source, "source_type": "file" if source == "football-data.co.uk" else "api"})
    source_id = _existing_source_id(conn, source)
    if source_id is None:
        raise MatchIdentityError("Data source could not be resolved")
    mapped = conn.execute(text("""SELECT entity_id FROM external_mappings
        WHERE data_source_id = :source_id AND entity_type = 'match'
          AND external_id = :external_id FOR UPDATE"""),
        {"source_id": source_id, "external_id": game_id}).first()
    params = dict(refs, start_time=kickoff.isoformat().replace("+00:00", "Z"), status=status,
                  home_score=match.get("home_score"), away_score=match.get("away_score"),
                  neutral_site=match.get("neutral_site"))
    if mapped:
        stored = conn.execute(text("""SELECT id, league_id, home_team_id, away_team_id, season_id
            FROM matches WHERE id = :match_id FOR UPDATE"""), {"match_id": mapped.entity_id}).first()
        if stored is None:
            raise MatchIdentityError(f"Dangling match mapping for {source}/{game_id}")
        for field in ("league_id", "home_team_id", "away_team_id", "season_id"):
            if field == "season_id" and (stored.season_id is None or refs[field] is None):
                continue
            if getattr(stored, field) != refs[field]:
                raise MatchIdentityError(f"Incompatible {field} change for {source}/{game_id}")
        params["match_id"] = stored.id
        row = conn.execute(text("""UPDATE matches SET
            season_id = COALESCE(:season_id, season_id), start_time = :start_time,
            status = :status, home_score = :home_score, away_score = :away_score,
            neutral_site = COALESCE(:neutral_site, neutral_site), updated_at = NOW()
            WHERE id = :match_id RETURNING id"""), params).first()
        if row is None:
            raise MatchIdentityError("Mapped match disappeared during update")
        action = "updated"
    else:
        row = conn.execute(text("""INSERT INTO matches
            (league_id, season_id, home_team_id, away_team_id, start_time, status,
             home_score, away_score, neutral_site)
            VALUES (:league_id, :season_id, :home_team_id, :away_team_id, :start_time,
                    :status, :home_score, :away_score, COALESCE(:neutral_site, FALSE))
            RETURNING id"""), params).first()
        if row is None:
            raise MatchIdentityError("Match insert did not return an ID")
        conn.execute(text("""INSERT INTO external_mappings
            (data_source_id, entity_type, entity_id, external_id)
            VALUES (:source_id, 'match', :entity_id, :external_id)"""),
            {"source_id": source_id, "entity_id": row.id, "external_id": game_id})
        action = "inserted"
    logger.info("%s match %s from %s", action, game_id, source)
    return (row.id, action) if return_action else row.id
