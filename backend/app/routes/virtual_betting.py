"""Virtual points only: no payments, deposits, or cash value."""
from decimal import Decimal
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.authentication import current_session, csrf_session
from app.database.db import get_db
from app.database.betting_tables import wallets, transactions, markets, outcomes, bets
from app.services.virtual_betting import ensure_wallet, topup, place_bet


def enabled():
    if not settings.VIRTUAL_BETTING_ENABLED:
        raise HTTPException(503, 'Virtual betting setup has not been enabled.')

router = APIRouter(tags=['virtual betting'], dependencies=[Depends(enabled)])

class RetryRequest(BaseModel):
    request_key: str = Field(min_length=1, max_length=100, pattern=r'^[A-Za-z0-9_-]+$')

class BetRequest(RetryRequest):
    match_id: int = Field(gt=0, strict=True)
    outcome_id: int = Field(gt=0, strict=True)
    stake: int = Field(gt=0, le=1_000_000, strict=True)
    expected_odds: Decimal = Field(gt=1, le=1000, max_digits=9, decimal_places=4)

class WalletOut(BaseModel):
    balance: int
    currency: str = 'virtual_points'

class BetOut(BaseModel):
    id: int
    user_id: int
    match_id: int
    outcome_id: int
    selection: str
    stake: int
    accepted_odds: Decimal
    potential_payout: int
    status: str
    request_key: str
    created_at: datetime

class TransactionOut(BaseModel):
    id: int
    user_id: int
    amount: int
    kind: str
    reference: str
    created_at: datetime

class OutcomeOut(BaseModel):
    id: int
    selection: str
    decimal_odds: Decimal

class MarketOut(BaseModel):
    market_id: int
    match_id: int
    market: str = 'single_match_winner'
    odds_source: str = 'synthetic_demo'
    is_open: bool
    outcomes: list[OutcomeOut]

@router.get('/wallet', response_model=WalletOut)
def wallet(session=Depends(current_session), db: Session=Depends(get_db)):
    ensure_wallet(db, session.user['id'])
    db.commit()
    return {'balance': db.execute(select(wallets.c.balance).where(wallets.c.user_id==session.user['id'])).scalar_one()}

@router.get('/wallet/transactions', response_model=list[TransactionOut])
def ledger(session=Depends(current_session), db: Session=Depends(get_db)):
    return db.execute(select(transactions).where(transactions.c.user_id==session.user['id']).order_by(transactions.c.id.desc())).mappings().all()

@router.post('/wallet/demo-topup', response_model=WalletOut)
def demo_topup(body: RetryRequest, session=Depends(csrf_session), db: Session=Depends(get_db)):
    return topup(db, session.user['id'], body.request_key)

@router.get('/matches/{match_id}/markets', response_model=list[MarketOut])
def match_markets(match_id: int, db: Session=Depends(get_db)):
    result=[]
    for market in db.execute(select(markets).where(markets.c.match_id==match_id)).mappings():
        result.append({'market_id':market['id'], 'match_id':match_id, 'is_open':market['is_open'],
                       'outcomes': db.execute(select(outcomes).where(outcomes.c.market_id==market['id'])).mappings().all()})
    return result

@router.post('/bets', response_model=BetOut, status_code=201)
def create_bet(body: BetRequest, session=Depends(csrf_session), db: Session=Depends(get_db)):
    return place_bet(db, session.user['id'], body)

@router.get('/bets', response_model=list[BetOut])
def list_bets(session=Depends(current_session), db: Session=Depends(get_db)):
    return db.execute(select(bets).where(bets.c.user_id==session.user['id']).order_by(bets.c.id.desc())).mappings().all()

@router.get('/bets/{bet_id}', response_model=BetOut)
def get_bet(bet_id: int, session=Depends(current_session), db: Session=Depends(get_db)):
    row=db.execute(select(bets).where(bets.c.id==bet_id,bets.c.user_id==session.user['id'])).mappings().first()
    if row is None: raise HTTPException(404, 'Bet not found.')
    return row
