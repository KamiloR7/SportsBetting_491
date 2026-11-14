"""Transactional single-match virtual betting. All amounts are integer points."""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from fastapi import HTTPException
from sqlalchemy import select, insert, update, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from app.database.betting_tables import wallets, transactions, markets, outcomes, bets


def ensure_wallet(db, user_id):
    # An upsert provides one starting balance and ledger entry under concurrent calls.
    dialect_insert = pg_insert if db.bind.dialect.name == 'postgresql' else sqlite_insert
    created = db.execute(dialect_insert(wallets).values(user_id=user_id, balance=1000)
                         .on_conflict_do_nothing(index_elements=['user_id']).returning(wallets.c.user_id)).first()
    if created:
        db.execute(insert(transactions).values(user_id=user_id, amount=1000, kind='INITIAL', reference='initial'))


def locked_wallet(db, user_id):
    ensure_wallet(db, user_id)
    return db.execute(select(wallets).where(wallets.c.user_id == user_id).with_for_update()).mappings().one()


def topup(db, user_id, key):
    wallet = locked_wallet(db, user_id)
    reference = 'topup:' + key
    previous = db.execute(select(transactions).where(transactions.c.user_id == user_id,
                                                    transactions.c.reference == reference)).mappings().first()
    if not previous:
        if wallet['balance'] > 2_000_000_000 - 1000:
            raise HTTPException(409, 'Demo balance limit reached.')
        db.execute(update(wallets).where(wallets.c.user_id == user_id).values(balance=wallet['balance'] + 1000))
        db.execute(insert(transactions).values(user_id=user_id, amount=1000, kind='DEMO_TOPUP', reference=reference))
    db.commit()
    return {'balance': db.execute(select(wallets.c.balance).where(wallets.c.user_id == user_id)).scalar_one(),
            'currency': 'virtual_points'}


def place_bet(db, user_id, request):
    # Lock order is match -> market -> wallet, shared with settlement.
    match = db.execute(text('SELECT m.*, l.abbreviation FROM matches m JOIN leagues l ON l.id=m.league_id WHERE m.id=:id FOR UPDATE OF m' if db.bind.dialect.name == 'postgresql' else 'SELECT m.*, l.abbreviation FROM matches m JOIN leagues l ON l.id=m.league_id WHERE m.id=:id'), {'id': request.match_id}).mappings().first()
    if not match:
        raise HTTPException(404, 'Match not found.')
    market = db.execute(select(markets).where(markets.c.match_id == request.match_id).with_for_update()).mappings().first()
    wallet = locked_wallet(db, user_id)
    previous = db.execute(select(bets).where(bets.c.user_id == user_id, bets.c.request_key == request.request_key)).mappings().first()
    if previous:
        if any(previous[k] != getattr(request, k) for k in ('match_id', 'outcome_id', 'stake')) or previous['accepted_odds'] != request.expected_odds:
            raise HTTPException(409, 'Request key already used for a different bet.')
        db.commit()
        return dict(previous)
    start = match['start_time']
    if isinstance(start, str): start = datetime.fromisoformat(start.replace('Z', '+00:00'))
    if start.tzinfo is None: start = start.replace(tzinfo=timezone.utc)
    if match['status'] != 'scheduled' or start <= datetime.now(timezone.utc) or not market or not market['is_open']:
        raise HTTPException(409, 'Betting is closed for this match.')
    outcome = db.execute(select(outcomes).where(outcomes.c.id == request.outcome_id,
                                               outcomes.c.market_id == market['id'])).mappings().first()
    if not outcome or match['abbreviation'] not in {'EPL','NFL','MLB'} or (outcome['selection'] == 'draw' and match['abbreviation'] != 'EPL'):
        raise HTTPException(422, 'Invalid betting outcome.')
    odds = outcome['decimal_odds']
    if odds <= 1 or odds > 1000 or odds != request.expected_odds:
        raise HTTPException(409, 'Odds changed or are unavailable. Refresh the market.')
    if wallet['balance'] < request.stake:
        raise HTTPException(409, 'Insufficient virtual points.')
    payout = int((Decimal(request.stake) * odds).to_integral_value(rounding=ROUND_DOWN))
    row = db.execute(insert(bets).values(user_id=user_id, match_id=request.match_id,
        outcome_id=request.outcome_id, selection=outcome['selection'], stake=request.stake,
        accepted_odds=odds, potential_payout=payout, status='PENDING', request_key=request.request_key)
        .returning(*bets.c)).mappings().one()
    db.execute(update(wallets).where(wallets.c.user_id == user_id).values(balance=wallet['balance']-request.stake))
    db.execute(insert(transactions).values(user_id=user_id, amount=-request.stake, kind='STAKE', reference=f"bet:{row['id']}:stake"))
    db.commit()
    return dict(row)


def settle_match(db, match_id, home_score=None, away_score=None, void=False):
    query = 'SELECT m.*, l.abbreviation FROM matches m JOIN leagues l ON l.id=m.league_id WHERE m.id=:id'
    if db.bind.dialect.name == 'postgresql': query += ' FOR UPDATE OF m'
    match = db.execute(text(query), {'id': match_id}).mappings().first()
    if not match: raise ValueError('Match not found.')
    if match['abbreviation'] not in {'EPL','NFL','MLB'}: raise ValueError('Unsupported league.')
    if not void and (type(home_score) is not int or type(away_score) is not int or min(home_score, away_score) < 0):
        raise ValueError('Nonnegative integer final scores are required.')
    already_completed = match['status'] in {'final','cancelled'}
    if already_completed:
        same_result = ((void and match['status'] == 'cancelled') or
                       (not void and match['status'] == 'final' and
                        match['home_score'] == home_score and match['away_score'] == away_score))
        if not same_result:
            raise ValueError('Match already settled with a different result.')
        # Match completion by another writer does not imply its bets were settled.
    db.execute(select(markets).where(markets.c.match_id == match_id).with_for_update()).all()
    # Two-way markets refund ties; EPL settles draw as its own outcome.
    refund = void or (home_score == away_score and match['abbreviation'] != 'EPL')
    winner = 'draw' if void or home_score == away_score else ('home' if home_score > away_score else 'away')
    pending = db.execute(select(bets).where(bets.c.match_id == match_id, bets.c.status == 'PENDING')
                         .order_by(bets.c.user_id, bets.c.id).with_for_update()).mappings().all()
    for bet in pending:
        wallet = locked_wallet(db, bet['user_id'])
        status = 'VOID' if refund else ('WON' if bet['selection'] == winner else 'LOST')
        amount = bet['stake'] if refund else (bet['potential_payout'] if status == 'WON' else 0)
        if amount:
            if wallet['balance'] + amount > 2_147_483_647: raise ValueError('Wallet balance limit exceeded.')
            db.execute(update(wallets).where(wallets.c.user_id == bet['user_id']).values(balance=wallet['balance'] + amount))
            db.execute(insert(transactions).values(user_id=bet['user_id'], amount=amount, kind='REFUND' if refund else 'PAYOUT', reference=f"bet:{bet['id']}:settlement"))
        db.execute(update(bets).where(bets.c.id == bet['id']).values(status=status))
    db.execute(update(markets).where(markets.c.match_id == match_id).values(is_open=False))
    if not already_completed:
        db.execute(text('UPDATE matches SET status=:status, home_score=:home, away_score=:away WHERE id=:id'),
                   {'status': 'cancelled' if void else 'final', 'home': None if void else home_score, 'away': None if void else away_score, 'id': match_id})
    db.commit()
    return {'match_id': match_id, 'settled': len(pending)}
