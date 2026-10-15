from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_id: int = Field(ge=1)


class PredictionProbabilities(BaseModel):
    home_win: float = Field(ge=0, le=1)
    not_home_win: float = Field(ge=0, le=1)


class PredictionHistory(BaseModel):
    home_games: int = Field(ge=0)
    away_games: int = Field(ge=0)


class PredictionResponse(BaseModel):
    match_id: int
    sport: Literal["NFL", "MLB", "EPL"]
    home_team_id: int
    home_team_name: str
    away_team_id: int
    away_team_name: str
    predicted_outcome: Literal["HOME_WIN", "NOT_HOME_WIN"]
    predicted_team_id: int | None
    predicted_team_name: str | None
    probabilities: PredictionProbabilities
    confidence: float = Field(ge=0, le=1)
    model_version: str
    history: PredictionHistory
