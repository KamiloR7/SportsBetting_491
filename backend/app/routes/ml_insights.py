from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.core.config import settings
from app.database.db import get_db
from app.services.ml_insights import read_evaluation, match_inputs
from app.services.prediction_service import MatchNotFoundError, UnsupportedSportError, InsufficientHistoryError

router = APIRouter(prefix="/insights", tags=["model insights"])


@router.get("/audit")
def evaluation_audit():
    if not settings.MODEL_ODDS_ENABLED:
        raise HTTPException(503, "Detailed evaluation requires configured market models.")
    try:
        return read_evaluation(settings.MARKET_MODEL_DIRECTORY)
    except (OSError, ValueError, KeyError, TypeError):
        raise HTTPException(503, "Verified evaluation is unavailable. Generate the local market audit report.") from None


@router.get("/matches/{match_id}/inputs")
def feature_inputs(match_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    from app.services.model_odds import configured_registry
    try:
        return match_inputs(db, match_id, configured_registry() if settings.MODEL_ODDS_ENABLED else None)
    except MatchNotFoundError:
        raise HTTPException(404, "Match not found.") from None
    except (UnsupportedSportError, InsufficientHistoryError) as exc:
        raise HTTPException(422, str(exc)) from None
    except SQLAlchemyError:
        raise HTTPException(503, "Match history is temporarily unavailable.") from None
