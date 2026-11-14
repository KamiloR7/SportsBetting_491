"""Explicit additive setup; never creates a database or alters existing tables."""
from sqlalchemy import String, inspect

from app.database.auth_tables import initialize_auth_tables, users
from app.database.betting_tables import initialize_betting_tables

BASE_TABLES = frozenset({
    'sports', 'leagues', 'seasons', 'teams', 'season_teams', 'matches',
    'model_versions', 'match_predictions', 'users', 'user_predictions',
    'data_sources', 'external_mappings', 'ingestion_runs',
})


def initialize_virtual_betting(engine):
    """Validate prerequisites before creating auth/betting objects atomically.

    The current base SQL must be applied explicitly to a fresh database first.
    Legacy databases require owner-reviewed migrations; no password defaults or
    account rewrites are performed here. Repeated compatible setup is a no-op.
    """
    with engine.begin() as connection:
        inspector = inspect(connection)
        missing = BASE_TABLES - set(inspector.get_table_names())
        if missing:
            raise ValueError('Base schema is incomplete. Apply the current base schema to a fresh database first.')
        columns = {column['name']: column for column in inspector.get_columns('users')}
        if not set(users.c.keys()) <= set(columns):
            raise ValueError('Existing users schema is incompatible. Review an explicit account migration before setup.')
        password = columns['password_hash']
        if (not isinstance(password['type'], String) or password['type'].length != 255
                or password['nullable']):
            raise ValueError('Existing users.password_hash must be VARCHAR(255) NOT NULL; review a migration before setup.')
        initialize_auth_tables(connection)
        initialize_betting_tables(connection)
