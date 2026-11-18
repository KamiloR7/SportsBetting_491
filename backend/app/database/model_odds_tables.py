"""Append-only pricing evidence and links from accepted bets to their quote."""
from sqlalchemy import Table, Column, ForeignKey, String, DateTime, Numeric, JSON, text
from app.database.auth_tables import metadata, user_id_type
from app.database.betting_tables import markets, bets

quotes = Table(
    "model_market_quotes", metadata,
    Column("id", user_id_type, primary_key=True),
    Column("market_id", user_id_type, ForeignKey(markets.c.id), nullable=False, index=True),
    Column("quote_key", String(64), nullable=False, index=True),
    Column("model_version", String(80), nullable=False),
    Column("training_end", DateTime(timezone=True), nullable=False),
    Column("margin", Numeric(7, 5), nullable=False),
    Column("probabilities", JSON, nullable=False),
    Column("prices", JSON, nullable=False),
    Column("features", JSON, nullable=False),
    Column("history", JSON, nullable=False),
    Column("generated_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
)
bet_quotes = Table(
    "model_bet_quotes", metadata,
    Column("bet_id", user_id_type, ForeignKey(bets.c.id), primary_key=True),
    Column("quote_id", user_id_type, ForeignKey(quotes.c.id), nullable=False),
)

def initialize_model_odds(engine):
    metadata.create_all(engine, tables=[quotes, bet_quotes])
