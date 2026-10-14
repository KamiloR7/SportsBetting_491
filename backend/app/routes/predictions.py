from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.schemas.predictions import PredictionOut

router = APIRouter(prefix="/predictions", tags=["predictions"])


def _prediction_from_row(row) -> PredictionOut:
    return PredictionOut(
        match_id=row.match_id,
        model_version_id=row.model_version_id,
        model_name=row.model_name,
        model_version=row.model_version,
        predicted_winner_id=row.predicted_winner_id,
        predicted_winner_name=row.predicted_winner_name,
        home_win_probability=row.home_win_probability,
        away_win_probability=row.away_win_probability,
        confidence=row.confidence,
        generated_at=row.generated_at,
    )


@router.post("/matches/{match_id}", response_model=PredictionOut)
def run_match_prediction(
    match_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    try:
        row = db.execute(
            text(
                """
                SELECT
                    mp.match_id,
                    mp.model_version_id,
                    mv.name AS model_name,
                    mv.version AS model_version,
                    mp.predicted_winner_id,
                    t.name AS predicted_winner_name,
                    mp.home_win_probability,
                    mp.away_win_probability,
                    mp.confidence,
                    mp.generated_at
                FROM match_predictions mp
                LEFT JOIN model_versions mv ON mv.id = mp.model_version_id
                LEFT JOIN teams t ON t.id = mp.predicted_winner_id
                WHERE mp.match_id = :match_id
                ORDER BY mp.generated_at DESC
                LIMIT 1
                """
            ),
            {"match_id": match_id},
        ).first()
    except OperationalError:
        raise HTTPException(
            status_code=503,
            detail="Prediction service is unavailable until the local database is running.",
        ) from None

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Prediction has not been generated for this match.",
        )

    return _prediction_from_row(row)
