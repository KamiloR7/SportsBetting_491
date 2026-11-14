"""Explicit route/access inventory. Unknown routes fail the assessment contract."""

import argparse
import json
import os
from pathlib import Path

from fastapi.routing import iter_route_contexts

PUBLIC = {
    ("GET", "/matches/{match_id}/markets"): "Public synthetic demo markets; betting opt-in required.",
    ("GET", "/health"): "Operational status and explicit data mode; no account data.",
    ("GET", "/sports"): "Public sport catalogue.",
    ("GET", "/leagues"): "Public league catalogue.",
    ("GET", "/teams"): "Public team catalogue.",
    ("GET", "/matches"): "Public match browsing.",
    ("GET", "/matches/history"): "Public completed-match results, not private account history.",
    ("GET", "/matches/{match_id}"): "Public match details.",
    ("POST", "/predictions"): "Public inference request; no account/private history write.",
    ("POST", "/predictions/matches/{match_id}"): "Public inference request; no account/private history write.",
    ("POST", "/auth/register"): "HTTPS-only public account creation; bcrypt storage, validation and duplicate handling.",
    ("GET", "/auth/csrf"): "HTTPS-only same-origin bootstrap; session-bound CSRF after login.",
    ("POST", "/auth/login"): "HTTPS-only pre-login CSRF challenge plus credentials and database throttle.",
}
PROTECTED = {
    ("GET", "/wallet"): "Betting opt-in and active-user session; only own wallet.",
    ("GET", "/wallet/transactions"): "Betting opt-in and active-user session; only own ledger.",
    ("POST", "/wallet/demo-topup"): "Betting opt-in, active session and CSRF; idempotent own-wallet refill.",
    ("POST", "/bets"): "Betting opt-in, active session and CSRF; transactional own-wallet debit.",
    ("GET", "/bets"): "Betting opt-in and active session; own bets only.",
    ("GET", "/bets/{bet_id}"): "Betting opt-in, active session and owner filter.",
    ("GET", "/auth/me"): "Valid active-user session; return only that user's public account fields.",
    ("POST", "/auth/logout"): "Valid session and bound CSRF; revoke only the presented session.",
    ("GET", "/auth/assessment/records/{record_id}"): "Assessment opt-in plus valid session and owner check.",
    ("PATCH", "/auth/assessment/records/{record_id}"): "Assessment opt-in, session, bound CSRF and owner check before writes.",
    ("GET", "/assessment/predictions/{prediction_id}"): "Valid active-user session and prediction ownership required.",
    ("PATCH", "/assessment/predictions/{prediction_id}"): "Valid session, bound CSRF token, and prediction ownership " "required before writes.",

}
DOCUMENTATION = {
    (method, path): "Public generated API documentation/schema; no runtime account records."
    for path in ["/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"]
    for method in ["GET", "HEAD"]
}


def route_inventory(application):
    policies = {**PUBLIC, **PROTECTED, **DOCUMENTATION}
    result = []
    for route in iter_route_contexts(application.routes):
        for method in sorted(route.methods or []):
            key = (method, route.path)
            if key not in policies:
                raise ValueError(f"Route lacks an approved access policy: {method} {route.path}")
            result.append({"method": method, "path": route.path,
                           "access": "protected" if key in PROTECTED else "public",
                           "rationale": policies[key]})
    return sorted(result, key=lambda row: (row["path"], row["method"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("build/sprint4/route-inventory.json"))
    args = parser.parse_args()
    # Metadata-only command; this does not connect to or validate a database.
    for name, value in {"DATABASE_HOST": "localhost", "DATABASE_PORT": "5432",
                        "DATABASE_NAME": "unused_inventory", "DATABASE_USER": "synthetic",
                        "DATABASE_PASSWORD": "unused"}.items():
        os.environ.setdefault(name, value)
    from app.main import app
    result = route_inventory(app)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        f"Classified {len(result)} method/route pairs; "
        f"{len(PROTECTED)} protected pairs."
    )
