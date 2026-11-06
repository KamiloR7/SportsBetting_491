from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.services.session_security import (
    get_session_user,
    validate_csrf_token,
)

router = APIRouter(
    prefix="/assessment/predictions",
    tags=["SOC 2 Authorization Assessment"],
)


class PredictionUpdate(BaseModel):
    predicted_winner_id: int = Field(gt=0)


def require_authenticated_user(request: Request) -> int:
    """Get the authenticated user ID from the session."""
    token = request.cookies.get("vigor_session")
    user_id = get_session_user(token)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    return user_id


@router.get("/{prediction_id}")
def read_owned_prediction(
    prediction_id: int,
    user_id: int = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    """Allow users to read only their own prediction."""

    result = db.execute(
        text(
            """
            SELECT id, user_id, match_id, predicted_winner_id
            FROM user_predictions
            WHERE id = :prediction_id
              AND user_id = :user_id
            """
        ),
        {
            "prediction_id": prediction_id,
            "user_id": user_id,
        },
    ).first()

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found",
        )

    return {
        "id": result.id,
        "user_id": result.user_id,
        "match_id": result.match_id,
        "predicted_winner_id": result.predicted_winner_id,
    }


@router.patch("/{prediction_id}")
def update_owned_prediction(
    prediction_id: int,
    update: PredictionUpdate,
    request: Request,
    user_id: int = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    """Update a prediction only when the user owns it."""

    session_token = request.cookies.get("vigor_session")
    csrf_token = request.headers.get("X-CSRF-Token")

    if not validate_csrf_token(session_token, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token",
        )

    result = db.execute(
        text(
            """
            UPDATE user_predictions AS up
            SET predicted_winner_id = :winner_id
            FROM matches AS m
            WHERE up.id = :prediction_id
              AND up.user_id = :user_id
              AND m.id = up.match_id
              AND (
                  :winner_id = m.home_team_id
                  OR :winner_id = m.away_team_id
              )
            RETURNING
                up.id,
                up.user_id,
                up.match_id,
                up.predicted_winner_id
            """
        ),
        {
            "prediction_id": prediction_id,
            "user_id": user_id,
            "winner_id": update.predicted_winner_id,
        },
    ).first()

    if result is None:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found or update not permitted",
        )

    db.commit()

    return {
        "id": result.id,
        "user_id": result.user_id,
        "match_id": result.match_id,
        "predicted_winner_id": result.predicted_winner_id,
    }