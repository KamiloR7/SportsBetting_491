"""Additive virtual-points schema; never initialized at application startup."""
from sqlalchemy import (Table, Column, Integer, String, ForeignKey, CheckConstraint,
                        UniqueConstraint, Numeric, DateTime, Boolean, text)
from app.database.auth_tables import metadata, users, user_id_type

# References describe existing tables without changing the original match schema.
if 'matches' not in metadata.tables:
    Table('matches', metadata, Column('id', user_id_type, primary_key=True))
wallets = Table('virtual_wallets', metadata,
    Column('user_id', user_id_type, ForeignKey('users.id'), primary_key=True),
    Column('balance', Integer, nullable=False), CheckConstraint('balance >= 0'))
markets = Table('demo_markets', metadata,
    Column('id', user_id_type, primary_key=True),
    Column('match_id', user_id_type, ForeignKey('matches.id'), nullable=False, unique=True),
    Column('is_open', Boolean, nullable=False, server_default=text('true')))
outcomes = Table('demo_outcomes', metadata,
    Column('id', user_id_type, primary_key=True),
    Column('market_id', user_id_type, ForeignKey('demo_markets.id'), nullable=False),
    Column('selection', String(10), nullable=False),
    Column('decimal_odds', Numeric(9,4), nullable=False),
    CheckConstraint("selection IN ('home','draw','away')"),
    CheckConstraint('decimal_odds > 1 AND decimal_odds <= 1000'),
    UniqueConstraint('market_id', 'selection'))
bets = Table('virtual_bets', metadata,
    Column('id', user_id_type, primary_key=True),
    Column('user_id', user_id_type, ForeignKey('users.id'), nullable=False),
    Column('match_id', user_id_type, ForeignKey('matches.id'), nullable=False),
    Column('outcome_id', user_id_type, ForeignKey('demo_outcomes.id'), nullable=False),
    Column('selection', String(10), nullable=False),
    Column('stake', Integer, nullable=False),
    Column('accepted_odds', Numeric(9,4), nullable=False),
    Column('potential_payout', Integer, nullable=False),
    Column('status', String(10), nullable=False, server_default='PENDING'),
    Column('request_key', String(100), nullable=False),
    Column('created_at', DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP')),
    CheckConstraint('stake > 0'), CheckConstraint('potential_payout >= stake'),
    CheckConstraint("status IN ('PENDING','WON','LOST','VOID')"),
    UniqueConstraint('user_id', 'request_key'))
transactions = Table('virtual_wallet_transactions', metadata,
    Column('id', user_id_type, primary_key=True),
    Column('user_id', user_id_type, ForeignKey('users.id'), nullable=False),
    Column('amount', Integer, nullable=False),
    Column('kind', String(20), nullable=False),
    Column('reference', String(120), nullable=False),
    Column('created_at', DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP')),
    UniqueConstraint('user_id', 'reference'))
BETTING_TABLES = [wallets, markets, outcomes, bets, transactions]


def initialize_betting_tables(engine):
    """Explicit additive setup; callers must obtain database-owner approval."""
    metadata.create_all(engine, tables=BETTING_TABLES)
