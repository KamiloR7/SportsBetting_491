"""Authenticated virtual-point parlays, with session CSRF and owner-scoped reads."""
from decimal import Decimal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field,ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.authentication import current_session,csrf_session
from app.database.db import get_db
from app.database.parlay_tables import parlays
from app.services.parlays import place_parlay,serialize_parlay
from app.routes.virtual_betting import RetryRequest


def enabled():
    if not (settings.VIRTUAL_BETTING_ENABLED and settings.PARLAYS_ENABLED and settings.MODEL_ODDS_ENABLED):
        raise HTTPException(503,"Model-priced parlays are not enabled.")
router=APIRouter(prefix="/parlays",tags=["virtual parlays"],dependencies=[Depends(enabled)])

class ParlayLegRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    match_id:int=Field(gt=0,strict=True)
    outcome_id:int=Field(gt=0,strict=True)
    expected_odds:Decimal=Field(gt=1,le=1000,max_digits=9,decimal_places=4)

class ParlayRequest(RetryRequest):
    model_config=ConfigDict(extra="forbid")
    stake:int=Field(gt=0,le=1_000_000,strict=True)
    legs:list[ParlayLegRequest]=Field(min_length=2,max_length=8)

@router.post("",status_code=201)
def create_parlay(body:ParlayRequest,session=Depends(csrf_session),db:Session=Depends(get_db)):
    return place_parlay(db,session.user["id"],body)

@router.get("")
def list_parlays(session=Depends(current_session),db:Session=Depends(get_db)):
    rows=db.execute(select(parlays).where(parlays.c.user_id==session.user["id"]).order_by(parlays.c.id.desc())).mappings().all()
    return [serialize_parlay(db,row) for row in rows]

@router.get("/{parlay_id}")
def get_parlay(parlay_id:int,session=Depends(current_session),db:Session=Depends(get_db)):
    row=db.execute(select(parlays).where(parlays.c.id==parlay_id,parlays.c.user_id==session.user["id"])).mappings().first()
    if row is None:raise HTTPException(404,"Parlay not found.")
    return serialize_parlay(db,row)
