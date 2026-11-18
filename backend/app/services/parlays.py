"""Atomic multi-match virtual bets and idempotent result settlement."""
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN, localcontext
from fastapi import HTTPException
from sqlalchemy import select, insert, update, text
from app.database.parlay_tables import parlays, legs
from app.database.betting_tables import markets, outcomes, wallets, transactions
from app.services.virtual_betting import locked_wallet
from app.services.model_odds import ensure_quote


def combined_return(stake, prices):
    with localcontext() as context:
        context.prec = 80
        combined = Decimal(1)
        for price in prices:
            value = Decimal(str(price))
            if not value.is_finite() or not Decimal(1) <= value <= Decimal(1000):
                raise ValueError("Invalid accepted odds")
            combined *= value
        if combined * stake > 2_000_000_000:
            raise ValueError("Potential return exceeds the 2-billion-point limit. Reduce the stake or selections.")
        combined = combined.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
        return combined, int((combined * stake).to_integral_value(rounding=ROUND_DOWN))


def request_fingerprint(request):
    payload = {"stake": request.stake, "legs": sorted((leg.match_id, leg.outcome_id, str(leg.expected_odds.normalize())) for leg in request.legs)}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def serialize_parlay(db, row):
    selections = db.execute(text("""SELECT pl.id,pl.match_id,pl.outcome_id,pl.selection,pl.accepted_odds,pl.status,
        pl.quote_id, ht.name AS home_team_name, at.name AS away_team_name, m.start_time,
        m.home_score,m.away_score,l.abbreviation AS sport
        FROM virtual_parlay_legs pl JOIN matches m ON m.id=pl.match_id
        JOIN teams ht ON ht.id=m.home_team_id JOIN teams at ON at.id=m.away_team_id
        JOIN leagues l ON l.id=m.league_id WHERE pl.parlay_id=:id ORDER BY pl.id"""), {"id": row["id"]}).mappings().all()
    effective_odds, current_return = combined_return(row["stake"], [leg["accepted_odds"] for leg in selections if leg["status"] != "VOID"])
    return {key: value for key,value in row.items() if key != "request_fingerprint"} | {
        "legs": [dict(leg) for leg in selections], "effective_combined_odds": effective_odds,
        "current_potential_payout": 0 if row["status"] == "LOST" else current_return}


def previous_request(db, user_id, request, fingerprint):
    row = db.execute(select(parlays).where(parlays.c.user_id==user_id, parlays.c.request_key==request.request_key)).mappings().first()
    if row is not None and row["request_fingerprint"] != fingerprint:
        raise HTTPException(409, "This request key was already used for a different parlay.")
    return row


def place_parlay(db, user_id, request):
    if not 2 <= len(request.legs) <= 8:
        raise HTTPException(422, "Choose 2–8 selections from different games.")
    if len({leg.match_id for leg in request.legs}) != len(request.legs):
        raise HTTPException(422, "Only one selection per game is allowed in a parlay.")
    fingerprint = request_fingerprint(request)
    previous = previous_request(db,user_id,request,fingerprint)
    if previous is not None:
        return serialize_parlay(db,previous)
    matches = {}
    # Match locks are globally ordered, then market locks, then the wallet.
    for leg in sorted(request.legs,key=lambda leg:leg.match_id):
        query="SELECT m.*, l.abbreviation FROM matches m JOIN leagues l ON l.id=m.league_id WHERE m.id=:id"
        if db.bind.dialect.name=="postgresql": query+=" FOR UPDATE OF m"
        match=db.execute(text(query),{"id":leg.match_id}).mappings().first()
        if match is None: raise HTTPException(404,"A selected match was not found.")
        start=match["start_time"]
        if isinstance(start,str):start=datetime.fromisoformat(start.replace("Z","+00:00"))
        if start.tzinfo is None:start=start.replace(tzinfo=timezone.utc)
        if match["status"]!="scheduled" or start<=datetime.now(timezone.utc):
            raise HTTPException(409,"A selected match has started or is closed. Remove it from the parlay.")
        matches[leg.match_id]=(match,start)
    accepted={}
    for leg in sorted(request.legs,key=lambda leg:leg.match_id):
        market=db.execute(select(markets).where(markets.c.match_id==leg.match_id).with_for_update()).mappings().first()
        if market is None or not market["is_open"]:raise HTTPException(409,"A selected market is closed.")
        quote=ensure_quote(db,matches[leg.match_id][0],market)
        outcome=db.execute(select(outcomes).where(outcomes.c.id==leg.outcome_id,outcomes.c.market_id==market["id"])).mappings().first()
        if outcome is None:raise HTTPException(422,"A selection does not belong to its match.")
        if outcome["decimal_odds"] != leg.expected_odds:
            raise HTTPException(409,"A selection’s odds changed. Refresh the parlay prices and review them before placing.")
        accepted[leg.match_id]=(outcome,quote)
    wallet=locked_wallet(db,user_id)
    previous=previous_request(db,user_id,request,fingerprint)
    if previous is not None:
        db.commit()
        return serialize_parlay(db,previous)
    if wallet["balance"]<request.stake:raise HTTPException(409,"Insufficient virtual points.")
    if any(start<=datetime.now(timezone.utc) for _,start in matches.values()):raise HTTPException(409,"A selected match has started.")
    try: combined,payout=combined_return(request.stake,[accepted[leg.match_id][0]["decimal_odds"] for leg in request.legs])
    except ValueError as exc:raise HTTPException(422,str(exc)) from None
    row=db.execute(insert(parlays).values(user_id=user_id,stake=request.stake,combined_odds=combined,potential_payout=payout,
        status="PENDING",request_key=request.request_key,request_fingerprint=fingerprint).returning(*parlays.c)).mappings().one()
    for leg in request.legs:
        outcome,quote=accepted[leg.match_id]
        db.execute(insert(legs).values(parlay_id=row["id"],match_id=leg.match_id,outcome_id=leg.outcome_id,quote_id=quote["id"],
            selection=outcome["selection"],accepted_odds=outcome["decimal_odds"],status="PENDING"))
    db.execute(update(wallets).where(wallets.c.user_id==user_id).values(balance=wallet["balance"]-request.stake))
    db.execute(insert(transactions).values(user_id=user_id,amount=-request.stake,kind="PARLAY_STAKE",reference=f"parlay:{row['id']}:stake"))
    db.commit()
    return serialize_parlay(db,row)


def prepare_settlement(db,match_id,winner,refund):
    """Lock affected parlays before any wallet locks; update this match's legs."""
    ids=select(legs.c.parlay_id).where(legs.c.match_id==match_id)
    affected=db.execute(select(parlays).where(parlays.c.id.in_(ids)).order_by(parlays.c.id).with_for_update()).mappings().all()
    for row in affected:
        leg=db.execute(select(legs).where(legs.c.parlay_id==row["id"],legs.c.match_id==match_id)).mappings().one()
        if leg["status"]=="PENDING":
            status="VOID" if refund else "WON" if leg["selection"]==winner else "LOST"
            db.execute(update(legs).where(legs.c.id==leg["id"]).values(status=status))
    return affected


def finish_settlement(db,affected):
    from app.services.virtual_betting import locked_wallet
    settled=0
    for row in affected:
        if row["status"]!="PENDING":continue
        selections=db.execute(select(legs).where(legs.c.parlay_id==row["id"])).mappings().all()
        statuses={leg["status"] for leg in selections}
        if "LOST" in statuses:status,amount="LOST",0
        elif "PENDING" in statuses:continue
        elif statuses=={"VOID"}:status,amount="VOID",row["stake"]
        else:
            status="WON"
            _,amount=combined_return(row["stake"],[leg["accepted_odds"] for leg in selections if leg["status"]=="WON"])
        if amount:
            wallet=locked_wallet(db,row["user_id"])
            if wallet["balance"]+amount>2_147_483_647:raise ValueError("Wallet balance limit exceeded.")
            db.execute(update(wallets).where(wallets.c.user_id==row["user_id"]).values(balance=wallet["balance"]+amount))
            db.execute(insert(transactions).values(user_id=row["user_id"],amount=amount,
                kind="PARLAY_REFUND" if status=="VOID" else "PARLAY_PAYOUT",reference=f"parlay:{row['id']}:settlement"))
        db.execute(update(parlays).where(parlays.c.id==row["id"]).values(status=status,actual_payout=amount,settled_at=datetime.now(timezone.utc)))
        settled+=1
    return settled
