from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MatchOut(BaseModel):
    id: int
    league_id: Optional[int]
    league_name: Optional[str]
    home_team_id: Optional[int]
    home_team_name: Optional[str]
    away_team_id: Optional[int]
    away_team_name: Optional[str]
    start_time: datetime
    status: Optional[str]
    home_score: Optional[int]
    away_score: Optional[int]
    neutral_site: bool
    home_primary_color: Optional[str] = None
    home_secondary_color: Optional[str] = None
    home_logo_url: Optional[str] = None
    away_primary_color: Optional[str] = None
    away_secondary_color: Optional[str] = None
    away_logo_url: Optional[str] = None
