from typing import Annotated, List, Literal, Optional
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.schemas.matches import MatchOut
from app.services.team_branding import match_brand_fields

router = APIRouter(prefix="/matches", tags=["matches"])

MatchStatus = Literal[
    "scheduled",
    "in_progress",
    "final",
    "postponed",
    "cancelled",
]


def _match_from_row(row) -> MatchOut:
    return MatchOut(
        id=row.id,
        league_id=row.league_id,
        league_name=row.league_name,
        home_team_id=row.home_team_id,
        home_team_name=row.home_team_name,
        away_team_id=row.away_team_id,
        away_team_name=row.away_team_name,
        start_time=row.start_time,
        status=row.status,
        home_score=row.home_score,
        away_score=row.away_score,
        neutral_site=row.neutral_site,
        **match_brand_fields(row.league_name,row.home_team_name,row.away_team_name),
    )


@router.get("", response_model=List[MatchOut])
def list_matches(
    league_id: Optional[int] = Query(default=None, ge=1),
    status: Optional[MatchStatus] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
    search: Annotated[str, Query(max_length=100)] = "",
    order: Literal["asc", "desc"] = "asc",
    view: Literal["all", "matchday", "today_results"] = "all",
    day_start: Optional[datetime] = None,
    day_end: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    if view in {"matchday", "today_results"}:
        if (day_start is None or day_end is None or day_start.tzinfo is None or day_end.tzinfo is None
                or not timedelta(hours=22) <= day_end - day_start <= timedelta(hours=26)):
            raise HTTPException(422, "Matchday requires timezone-aware local-day boundaries, 22–26 hours apart.")
        if status is not None:
            raise HTTPException(422, "Choose matchday or a status filter, not both.")
        day_start, day_end = day_start.astimezone(timezone.utc), day_end.astimezone(timezone.utc)
    try:
        rows = db.execute(
            text(
                """
                SELECT
                    m.id,
                    m.league_id,
                    l.name AS league_name,
                    m.home_team_id,
                    ht.name AS home_team_name,
                    m.away_team_id,
                    at.name AS away_team_name,
                    m.start_time,
                    m.status,
                    m.home_score,
                    m.away_score,
                    m.neutral_site
                FROM matches m
                LEFT JOIN leagues l ON l.id = m.league_id
                LEFT JOIN teams ht ON ht.id = m.home_team_id
                LEFT JOIN teams at ON at.id = m.away_team_id
                WHERE (:league_id IS NULL OR m.league_id = :league_id)
                  AND (:status IS NULL OR m.status = :status)
                  AND (:search = '' OR LOWER(ht.name) LIKE :pattern OR LOWER(at.name) LIKE :pattern)
                  AND (:matchday = false OR (m.status = 'in_progress' AND m.start_time >= :active_since)
                       OR (m.status = 'scheduled' AND m.start_time >= :day_start))
                  AND (:today_results = false OR (m.status = 'final' AND m.start_time >= :day_start AND m.start_time < :day_end))
                ORDER BY CASE WHEN :matchday THEN CASE
                    WHEN m.status = 'in_progress' THEN 0
                    WHEN m.start_time >= :day_start AND m.start_time < :day_end THEN 1
                    ELSE 2 END ELSE 0 END,
                    CASE WHEN :descending THEN m.start_time END DESC, m.start_time, m.id
                LIMIT :limit OFFSET :offset
                """
            ),
            {
                "league_id": league_id,
                "status": status,
                "limit": limit, "offset": offset, "search": search, "pattern": "%" + search.lower() + "%", "descending": order == "desc",
                "matchday": view == "matchday", "today_results": view == "today_results", "day_start": day_start, "day_end": day_end,
                "active_since": day_start - timedelta(days=1) if day_start else None,
            },
        ).all()
    except OperationalError:
        raise HTTPException(status_code=503, detail="Match data is unavailable.") from None

    return [_match_from_row(row) for row in rows]


@router.get("/history", response_model=List[MatchOut])
def match_history(
    league_id: Optional[int] = Query(default=None, ge=1),
    team_id: Optional[int] = Query(default=None, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
    before: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    if before is not None and before.tzinfo is None:
        raise HTTPException(422, "History cutoff must include a timezone.")
    try:
        rows = db.execute(
            text(
                """
                SELECT
                    m.id,
                    m.league_id,
                    l.name AS league_name,
                    m.home_team_id,
                    ht.name AS home_team_name,
                    m.away_team_id,
                    at.name AS away_team_name,
                    m.start_time,
                    m.status,
                    m.home_score,
                    m.away_score,
                    m.neutral_site
                FROM matches m
                LEFT JOIN leagues l ON l.id = m.league_id
                LEFT JOIN teams ht ON ht.id = m.home_team_id
                LEFT JOIN teams at ON at.id = m.away_team_id
                WHERE m.status = 'final'
                  AND (:league_id IS NULL OR m.league_id = :league_id)
                  AND (:team_id IS NULL OR m.home_team_id = :team_id OR m.away_team_id = :team_id)
                  AND (:before IS NULL OR m.start_time < :before)
                ORDER BY m.start_time DESC
                LIMIT :limit
                """
            ),
            {
                "league_id": league_id,
                "team_id": team_id,
                "limit": limit,
                "before": before,
            },
        ).all()
    except OperationalError:
        raise HTTPException(status_code=503, detail="Match history is unavailable.") from None

    return [_match_from_row(row) for row in rows]


@router.get("/{match_id}", response_model=MatchOut)
def get_match(
    match_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    try:
        row = db.execute(
            text(
                """
                SELECT
                    m.id,
                    m.league_id,
                    l.name AS league_name,
                    m.home_team_id,
                    ht.name AS home_team_name,
                    m.away_team_id,
                    at.name AS away_team_name,
                    m.start_time,
                    m.status,
                    m.home_score,
                    m.away_score,
                    m.neutral_site
                FROM matches m
                LEFT JOIN leagues l ON l.id = m.league_id
                LEFT JOIN teams ht ON ht.id = m.home_team_id
                LEFT JOIN teams at ON at.id = m.away_team_id
                WHERE m.id = :match_id
                """
            ),
            {"match_id": match_id},
        ).first()
    except OperationalError:
        raise HTTPException(
            status_code=503,
            detail="Match data is unavailable.",
        ) from None

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Match not found.",
        )

    return _match_from_row(row)
