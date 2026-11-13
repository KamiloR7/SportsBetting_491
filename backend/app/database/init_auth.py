"""Explicit additive auth schema setup for an existing configured database.

Read the setup guide first. This does not initialize users, seed data, or run on
application startup. PostgreSQL assessment tests initialize their own schemas.
"""

import argparse


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Create the four additive auth tables in the configured database")
    args = parser.parse_args()
    if not args.apply:
        parser.error("Explicit --apply is required; review DATABASE_* configuration first")
    from app.database.auth_tables import initialize_auth_tables
    from app.database.db import engine
    initialize_auth_tables(engine)
    print("Auth schema initialized; existing users/data are retained. No test results implied.")
