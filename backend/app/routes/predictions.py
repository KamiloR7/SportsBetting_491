from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.schemas.predictions import PredictionRequest, PredictionResponse
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
