"""Explicit additive model-pricing setup for the local project database."""
from app.database.db import engine
from app.database.model_odds_tables import initialize_model_odds

if __name__ == "__main__":
    if engine.url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise SystemExit("Only local database setup is supported")
    initialize_model_odds(engine)
    print("Model quote history and accepted-bet quote links initialized.")
