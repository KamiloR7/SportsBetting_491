"""Virtual points only: no payments, deposits, or cash value."""
from decimal import Decimal
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, text
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

class TopupRequest(RetryRequest):
    amount: int = Field(default=1000, gt=0, le=1_000_000, strict=True)

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
    odds_source: str = "legacy_demo"
    pricing_model_version: str | None = None
    home_team_name: str | None = None
    away_team_name: str | None = None
    start_time: datetime | None = None
    sport: str | None = None

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
    probabilities: dict[str, float] | None = None
    pricing_margin: float | None = None
    model_version: str | None = None
    quoted_at: datetime | None = None
    implied_margin: float | None = None

@router.get('/wallet', response_model=WalletOut)
def wallet(session=Depends(current_session), db: Session=Depends(get_db)):
    ensure_wallet(db, session.user['id'])
    db.commit()
    return {'balance': db.execute(select(wallets.c.balance).where(wallets.c.user_id==session.user['id'])).scalar_one()}

@router.get('/wallet/transactions', response_model=list[TransactionOut])
def ledger(session=Depends(current_session), db: Session=Depends(get_db)):
    return db.execute(select(transactions).where(transactions.c.user_id==session.user['id']).order_by(transactions.c.id.desc())).mappings().all()

@router.post('/wallet/demo-topup', response_model=WalletOut)
def demo_topup(body: TopupRequest, session=Depends(csrf_session), db: Session=Depends(get_db)):
    return topup(db, session.user['id'], body.request_key, body.amount)

@router.get('/matches/{match_id}/markets', response_model=list[MarketOut])
def match_markets(match_id: int, db: Session=Depends(get_db)):
    result=[]
    if settings.MODEL_ODDS_ENABLED:
        from app.services.model_odds import ensure_quote, latest_quote
        query = "SELECT m.*, l.abbreviation FROM matches m JOIN leagues l ON l.id=m.league_id WHERE m.id=:id"
        if db.bind.dialect.name == "postgresql": query += " FOR UPDATE OF m"
        match = db.execute(text(query), {"id": match_id}).mappings().first()
        if match is None: raise HTTPException(404, "Match not found.")
    for market in db.execute(select(markets).where(markets.c.match_id==match_id).with_for_update()).mappings():
        quote = None
        if settings.MODEL_ODDS_ENABLED:
            start = match["start_time"]
            if isinstance(start, str): start = datetime.fromisoformat(start.replace("Z", "+00:00"))
            if start.tzinfo is None: start = start.replace(tzinfo=timezone.utc)
            if market["is_open"] and match["status"] == "scheduled" and start > datetime.now(timezone.utc):
                quote = ensure_quote(db, match, market)
            else:
                quote = latest_quote(db, market["id"])
        rows = db.execute(select(outcomes).where(outcomes.c.market_id==market['id'])).mappings().all()
        item = {'market_id':market['id'], 'match_id':match_id, 'is_open':market['is_open'], 'outcomes':rows}
        if settings.MODEL_ODDS_ENABLED:
            item['is_open'] = bool(market['is_open'] and match['status'] == 'scheduled' and start > datetime.now(timezone.utc))
        if quote:
            item.update(odds_source="model_derived", probabilities=quote["probabilities"],
                        pricing_margin=float(quote["margin"]), model_version=quote["model_version"], quoted_at=quote["generated_at"],
                        implied_margin=sum(1/float(row["decimal_odds"]) for row in rows)-1)
        result.append(item)
    db.commit()
    return result

@router.post('/bets', response_model=BetOut, status_code=201, response_model_exclude_unset=True)
def create_bet(body: BetRequest, session=Depends(csrf_session), db: Session=Depends(get_db)):
    row = place_bet(db, session.user['id'], body)
    return with_quote_source(db, row)

@router.get('/bets', response_model=list[BetOut], response_model_exclude_unset=True)
def list_bets(session=Depends(current_session), db: Session=Depends(get_db)):
    rows = db.execute(select(bets).where(bets.c.user_id==session.user['id']).order_by(bets.c.id.desc())).mappings().all()
    return [with_quote_source(db, row) for row in rows]

@router.get('/bets/{bet_id}', response_model=BetOut, response_model_exclude_unset=True)
def get_bet(bet_id: int, session=Depends(current_session), db: Session=Depends(get_db)):
    row=db.execute(select(bets).where(bets.c.id==bet_id,bets.c.user_id==session.user['id'])).mappings().first()
    if row is None: raise HTTPException(404, 'Bet not found.')
    return with_quote_source(db, row)


def with_quote_source(db, row):
    if not settings.MODEL_ODDS_ENABLED:
        return row
    from app.database.model_odds_tables import quotes, bet_quotes
    version = db.execute(select(quotes.c.model_version).join(bet_quotes, bet_quotes.c.quote_id == quotes.c.id)
                         .where(bet_quotes.c.bet_id == row["id"])).scalar_one_or_none()
    context = db.execute(text("SELECT ht.name AS home_team_name, at.name AS away_team_name,m.start_time,l.abbreviation AS sport FROM matches m JOIN teams ht ON ht.id=m.home_team_id JOIN teams at ON at.id=m.away_team_id JOIN leagues l ON l.id=m.league_id WHERE m.id=:id"), {"id":row["match_id"]}).mappings().first()
    return {**row, **(dict(context) if context else {}), "odds_source": "model_derived" if version else "legacy_demo", "pricing_model_version": version}
