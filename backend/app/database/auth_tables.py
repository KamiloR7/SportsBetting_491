"""Additive auth tables. Initialization is explicit, never on application import.

The users table describes the existing registration schema. The assessment
records are synthetic examples, not production prediction-history records.
"""

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON,
    MetaData, String, Table, Text, text,
)

metadata = MetaData()
user_id_type = BigInteger().with_variant(Integer, "sqlite")
users = Table(
    "users", metadata,
    Column("id", user_id_type, primary_key=True),
    Column("email", String(254), nullable=False, unique=True),
    Column("username", String(80), unique=True),
    Column("display_name", String(120)),
    Column("password_hash", String(255), nullable=False),
    Column("is_active", Boolean, server_default=text("true")),
    Column("created_at", DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")),
)
sessions = Table(
    "auth_sessions", metadata,
    Column("token_digest", String(64), primary_key=True),
    Column("user_id", user_id_type, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("csrf_token", String(43), nullable=False),
    Column("expires_at", Float, nullable=False, index=True),
)
challenges = Table(
    "auth_csrf_challenges", metadata,
    Column("nonce_digest", String(64), primary_key=True),
    Column("csrf_token", String(43), nullable=False),
    Column("expires_at", Float, nullable=False, index=True),
)
attempts = Table(
    "auth_login_attempts", metadata,
    Column("key_digest", String(64), primary_key=True),
    Column("window_start", Float, nullable=False),
    Column("failure_count", Integer, nullable=False),
    Column("blocked_until", Float, nullable=False),
    Column("failure_times", JSON, nullable=False, server_default=text("'[]'")),
)
assessment_records = Table(
    "auth_assessment_records", metadata,
    Column("id", user_id_type, primary_key=True),
    Column("owner_id", user_id_type, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("note", Text, nullable=False),
)
AUTH_TABLES = [sessions, challenges, attempts, assessment_records]


def initialize_auth_tables(engine):
    """Existing users schema must already be installed (see setup guide)."""
    metadata.create_all(engine, tables=AUTH_TABLES)
