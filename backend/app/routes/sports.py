from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.schemas.sports import LeagueOut, SportOut, SportSummary, TeamOut

router = APIRouter(tags=["sports"])


def _sport_summary(row) -> Optional[SportSummary]:
    if row.sport_id is None:
        return None
    return SportSummary(id=row.sport_id, name=row.sport_name, slug=row.sport_slug)


@router.get("/sports", response_model=List[SportOut])
def list_sports(db: Session = Depends(get_db)):
    rows = db.execute(text("SELECT id, name, slug FROM sports ORDER BY name")).all()
    return [SportOut(id=row.id, name=row.name, slug=row.slug) for row in rows]


@router.get("/leagues", response_model=List[LeagueOut])
def list_leagues(db: Session = Depends(get_db)):
    rows = db.execute(
        text(
            """
            SELECT
                l.id, l.name, l.abbreviation, l.country, l.active,
                s.id AS sport_id, s.name AS sport_name, s.slug AS sport_slug
            FROM leagues l
            LEFT JOIN sports s ON s.id = l.sport_id
            ORDER BY l.name
            """
        )
    ).all()
    return [
        LeagueOut(
            id=row.id,
            name=row.name,
            abbreviation=row.abbreviation,
            country=row.country,
            active=row.active,
            sport=_sport_summary(row),
        )
        for row in rows
    ]


@router.get("/teams", response_model=List[TeamOut])
def list_teams(db: Session = Depends(get_db)):
    rows = db.execute(
        text(
            """
            SELECT
                t.id, t.name, t.abbreviation, t.city, t.active,
                s.id AS sport_id, s.name AS sport_name, s.slug AS sport_slug
            FROM teams t
            LEFT JOIN sports s ON s.id = t.sport_id
            ORDER BY t.name
            """
        )
    ).all()
    return [
        TeamOut(
            id=row.id,
            name=row.name,
            abbreviation=row.abbreviation,
            city=row.city,
            active=row.active,
            sport=_sport_summary(row),
        )
        for row in rows
    ]
