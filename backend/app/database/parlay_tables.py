"""Explicit additive parlay schema; accepted leg odds are immutable snapshots."""
from sqlalchemy import Table, Column, ForeignKey, String, DateTime, Numeric, Integer, CheckConstraint, UniqueConstraint, text
from app.database.auth_tables import metadata, user_id_type, users
from app.database.betting_tables import outcomes
from app.database.model_odds_tables import quotes

parlays = Table("virtual_parlays", metadata,
    Column("id", user_id_type, primary_key=True),
    Column("user_id", user_id_type, ForeignKey(users.c.id), nullable=False, index=True),
    Column("stake", Integer, nullable=False),
    Column("combined_odds", Numeric(20,8), nullable=False),
    Column("potential_payout", Integer, nullable=False),
    Column("actual_payout", Integer),
    Column("status", String(10), nullable=False, server_default="PENDING"),
    Column("request_key", String(100), nullable=False),
    Column("request_fingerprint", String(64), nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")),
    Column("settled_at", DateTime(timezone=True)),
    UniqueConstraint("user_id", "request_key"),
    CheckConstraint("stake > 0"), CheckConstraint("potential_payout >= stake"),
    CheckConstraint("status IN ('PENDING','WON','LOST','VOID')"))
legs = Table("virtual_parlay_legs", metadata,
    Column("id", user_id_type, primary_key=True),
    Column("parlay_id", user_id_type, ForeignKey(parlays.c.id), nullable=False, index=True),
    Column("match_id", user_id_type, ForeignKey("matches.id"), nullable=False, index=True),
    Column("outcome_id", user_id_type, ForeignKey(outcomes.c.id), nullable=False),
    Column("quote_id", user_id_type, ForeignKey(quotes.c.id), nullable=False),
    Column("selection", String(10), nullable=False),
    Column("accepted_odds", Numeric(9,4), nullable=False),
    Column("status", String(10), nullable=False, server_default="PENDING"),
    UniqueConstraint("parlay_id", "match_id"),
    CheckConstraint("accepted_odds > 1 AND accepted_odds <= 1000"),
    CheckConstraint("selection IN ('home','away','draw')"),
    CheckConstraint("status IN ('PENDING','WON','LOST','VOID')"))

def initialize_parlays(engine):
    metadata.create_all(engine, tables=[parlays, legs])
