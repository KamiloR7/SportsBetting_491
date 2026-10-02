from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.schemas.matches import MatchOut

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
    )


@router.get("", response_model=List[MatchOut])
def list_matches(
    league_id: Optional[int] = None,
    status: Optional[MatchStatus] = None,
    db: Session = Depends(get_db),
):
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
            ORDER BY m.start_time
            """
        ),
        {
            "league_id": league_id,
            "status": status,
        },
    ).all()

    return [_match_from_row(row) for row in rows]


@router.get("/history", response_model=List[MatchOut])
def match_history(
    league_id: Optional[int] = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
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
            ORDER BY m.start_time DESC
            LIMIT :limit
            """
        ),
        {
            "league_id": league_id,
            "limit": limit,
        },
    ).all()

    return [_match_from_row(row) for row in rows]


@router.get("/{match_id}", response_model=MatchOut)
def get_match(
    match_id: int,
    db: Session = Depends(get_db),
):
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

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Match not found.",
        )

    return _match_from_row(row)