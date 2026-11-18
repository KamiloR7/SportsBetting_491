"""Explicit own-account demo reset. Match locks preserve settlement ordering."""
from fastapi import HTTPException
from sqlalchemy import select, delete, insert, update, text, inspect
from app.database.betting_tables import bets, wallets, transactions
from app.services.virtual_betting import locked_wallet


def reset_demo(db, user_id, key):
    from app.database.parlay_tables import parlays, legs
    from app.database.model_odds_tables import bet_quotes
    schema = inspect(db.connection())
    has_parlays = schema.has_table(parlays.name)
    has_quotes = schema.has_table(bet_quotes.name)
    reference = "reset:" + key
    def match_ids():
        ids = set(db.execute(select(bets.c.match_id).where(bets.c.user_id == user_id)).scalars())
        if has_parlays:
            ids.update(db.execute(select(legs.c.match_id).join(parlays, legs.c.parlay_id == parlays.c.id).where(parlays.c.user_id == user_id)).scalars())
        return ids
    for attempt in range(3):
        ids = match_ids()
        for match_id in sorted(ids):
            query = "SELECT id FROM matches WHERE id=:id" + (" FOR UPDATE" if db.bind.dialect.name == "postgresql" else "")
            db.execute(text(query), {"id": match_id}).all()
        if has_parlays:
            db.execute(select(parlays.c.id).where(parlays.c.user_id == user_id).order_by(parlays.c.id).with_for_update()).all()
        wallet = locked_wallet(db, user_id)
        # A same-key retry must not erase anything placed after the first reset.
        if db.execute(select(transactions.c.id).where(transactions.c.user_id == user_id, transactions.c.reference == reference)).first():
            db.commit()
            return {"balance": wallet["balance"], "currency": "virtual_points"}
        # A placement may have completed while we acquired match locks. Retry in
        # global match order before deleting it; placements still waiting on the
        # wallet belong to the new account round and debit the reset balance.
        if not match_ids().issubset(ids):
            db.rollback()
            continue
        if has_parlays:
            own_parlays = select(parlays.c.id).where(parlays.c.user_id == user_id)
            db.execute(delete(legs).where(legs.c.parlay_id.in_(own_parlays)))
            db.execute(delete(parlays).where(parlays.c.user_id == user_id))
        if has_quotes:
            db.execute(delete(bet_quotes).where(bet_quotes.c.bet_id.in_(select(bets.c.id).where(bets.c.user_id == user_id))))
        db.execute(delete(bets).where(bets.c.user_id == user_id))
        # Keep reset receipts for idempotency, hidden below the newest receipt
        # in ledger reads. Other users and public match/model data are untouched.
        db.execute(delete(transactions).where(transactions.c.user_id == user_id, transactions.c.kind != "DEMO_RESET"))
        db.execute(update(wallets).where(wallets.c.user_id == user_id).values(balance=1000))
        db.execute(insert(transactions).values(user_id=user_id, amount=1000, kind="DEMO_RESET", reference=reference))
        db.commit()
        return {"balance": 1000, "currency": "virtual_points"}
    raise HTTPException(409, "Your bets changed during reset. Please try again.")
