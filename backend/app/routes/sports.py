from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.exc import OperationalError
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.database.seed_data import LEAGUES, SPORTS, TEAMS
from app.schemas.sports import LeagueOut, SportOut, SportSummary, TeamOut

router = APIRouter(tags=["sports"])


def _sport_summary(row) -> Optional[SportSummary]:
    if row.sport_id is None:
        return None
    return SportSummary(id=row.sport_id, name=row.sport_name, slug=row.sport_slug)


def _fallback_sport_ids() -> dict[str, int]:
    return {sport["slug"]: index for index, sport in enumerate(SPORTS, start=1)}


def _fallback_sport_summary(sport_slug: str) -> SportSummary:
    sport_ids = _fallback_sport_ids()
    sport = next(item for item in SPORTS if item["slug"] == sport_slug)
    return SportSummary(
        id=sport_ids[sport_slug],
        name=sport["name"],
        slug=sport_slug,
    )


def _fallback_sports() -> List[SportOut]:
    sport_ids = _fallback_sport_ids()
    return [
        SportOut(id=sport_ids[sport["slug"]], name=sport["name"], slug=sport["slug"])
        for sport in sorted(SPORTS, key=lambda item: item["name"])
    ]


def _fallback_leagues() -> List[LeagueOut]:
    return [
        LeagueOut(
            id=index,
            name=league["name"],
            abbreviation=league["abbreviation"],
            country=league["country"],
            active=True,
            sport=_fallback_sport_summary(league["sport_slug"]),
        )
        for index, league in enumerate(
            sorted(LEAGUES, key=lambda item: item["name"]),
            start=1,
        )
    ]


def _fallback_teams() -> List[TeamOut]:
    return [
        TeamOut(
            id=index,
            name=team["name"],
            abbreviation=team["abbreviation"],
            city=team["city"],
            active=True,
            sport=_fallback_sport_summary(team["sport_slug"]),
        )
        for index, team in enumerate(
            sorted(TEAMS, key=lambda item: item["name"]),
            start=1,
        )
    ]


@router.get("/sports", response_model=List[SportOut])
def list_sports(db: Session = Depends(get_db)):
    try:
        rows = db.execute(text("SELECT id, name, slug FROM sports ORDER BY name")).all()
    except OperationalError:
        return _fallback_sports()

    return [SportOut(id=row.id, name=row.name, slug=row.slug) for row in rows]


@router.get("/leagues", response_model=List[LeagueOut])
def list_leagues(db: Session = Depends(get_db)):
    try:
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
    except OperationalError:
        return _fallback_leagues()

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
    try:
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
    except OperationalError:
        return _fallback_teams()

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
