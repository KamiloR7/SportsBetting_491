"""Explicit additive setup; existing bets and wallets are preserved."""
from app.database.db import engine
from app.database.parlay_tables import initialize_parlays
if __name__=="__main__":
    if engine.url.host not in {"localhost","127.0.0.1","::1"}:raise SystemExit("Local database required")
    initialize_parlays(engine)
    print("Parlay headers and leg snapshots initialized.")
