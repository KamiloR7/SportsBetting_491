from typing import Optional

from pydantic import BaseModel


class SportOut(BaseModel):
    id: int
    name: str
    slug: str


class SportSummary(BaseModel):
    id: int
    name: str
    slug: str


class LeagueOut(BaseModel):
    id: int
    name: str
    abbreviation: Optional[str] = None
    country: Optional[str] = None
    active: Optional[bool] = None
    sport: Optional[SportSummary] = None


class TeamOut(BaseModel):
    id: int
    name: str
    abbreviation: Optional[str] = None
    city: Optional[str] = None
    active: Optional[bool] = None
    sport: Optional[SportSummary] = None
