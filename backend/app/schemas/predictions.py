from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PredictionOut(BaseModel):
    match_id: int
    model_version_id: Optional[int] = None
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    predicted_winner_id: Optional[int] = None
    predicted_winner_name: Optional[str] = None
    home_win_probability: Optional[float] = None
    away_win_probability: Optional[float] = None
    confidence: Optional[float] = None
    generated_at: Optional[datetime] = None
