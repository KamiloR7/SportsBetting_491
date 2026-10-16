from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import Path
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.schemas.predictions import PredictionOut, PredictionRequest, PredictionResponse
from app.services.match_prediction import predict_probabilities
from app.services.prediction_service import (
    MatchNotFoundError,
    PredictionService,
    PredictionUnavailableError,
    UnsupportedSportError,
    get_prediction_service,
)

router = APIRouter(prefix="/predictions", tags=["predictions"])


def prediction_service_dependency(db: Session = Depends(get_db)) -> PredictionService:
    return get_prediction_service(db)


@router.post("", response_model=PredictionResponse)
def create_prediction(
    request: PredictionRequest,
    service: PredictionService = Depends(prediction_service_dependency),
):
    try:
        return service.predict(request.match_id)
    except MatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except UnsupportedSportError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except PredictionUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Prediction service is temporarily unavailable.",
        ) from exc


@router.post("/matches/{match_id}", response_model=PredictionOut)
def run_match_prediction(
    match_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    try:
        match = db.execute(
            text(
                """
                SELECT m.id, m.league_id, l.abbreviation AS sport,
                       m.home_team_id, ht.name AS home_team_name,
                       m.away_team_id, at.name AS away_team_name,
                       m.start_time, m.status
                FROM matches m
                JOIN leagues l ON l.id = m.league_id
                JOIN teams ht ON ht.id = m.home_team_id
                JOIN teams at ON at.id = m.away_team_id
                WHERE m.id = :match_id
                """
            ),
            {"match_id": match_id},
        ).first()
        if match is None:
            raise HTTPException(status_code=404, detail="Match not found.")
        if match.status != "scheduled":
            raise HTTPException(status_code=422, detail="Only scheduled matches can be predicted.")
        if match.sport not in {"NFL", "MLB", "EPL"}:
            raise HTTPException(status_code=422, detail="This league has no prediction model.")

        start_time = match.start_time
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        start_day = start_time.astimezone(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        history = db.execute(
            text(
                """
                SELECT home_team_id, away_team_id, home_score, away_score
                FROM matches
                WHERE league_id = :league_id
                  AND status = 'final'
                  AND start_time < :start_day
                  AND home_score IS NOT NULL
                  AND away_score IS NOT NULL
                ORDER BY start_time
                """
            ),
            {"league_id": match.league_id, "start_day": start_day},
        ).all()
    except OperationalError:
        raise HTTPException(status_code=503, detail="Match data is unavailable.") from None

    try:
        result = predict_probabilities(
            match.sport, match.home_team_id, match.away_team_id, history
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    winner_id = {
        "home_win": match.home_team_id,
        "away_win": match.away_team_id,
    }.get(result["predicted_outcome"])
    winner_name = {
        "home_win": match.home_team_name,
        "away_win": match.away_team_name,
    }.get(result["predicted_outcome"])
    return PredictionOut(
        match_id=match_id,
        model_name="multisport_baseline",
        predicted_winner_id=winner_id,
        predicted_winner_name=winner_name,
        generated_at=datetime.now(timezone.utc),
        **result,
    )
