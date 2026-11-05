"""Database-backed prototype sessions, CSRF, and account-keyed login throttling."""

import hashlib
import re
import secrets
import time
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database.auth_tables import sessions, users
from app.database.db import get_db

SESSION_COOKIE = "__Host-vigor_session"
CHALLENGE_COOKIE = "__Host-vigor_csrf"
SESSION_SECONDS = 30 * 60
WINDOW_SECONDS = 5 * 60
BLOCK_SECONDS = 15 * 60
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}\Z")


def now_seconds() -> float:
    """Inject a controlled clock in tests, not shortened security settings."""
    return time.time()


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def require_https(request: Request):
    if request.url.scheme != "https":
        raise HTTPException(403, "HTTPS is required for authentication.")


def check_request_origin(request: Request):
    """No trusted forwarding header or permissive cross-origin policy here."""
    require_https(request)
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "Cross-site authentication request denied.")
    origin = request.headers.get("origin")
    if origin is not None and origin != str(request.base_url).rstrip("/"):
        raise HTTPException(403, "Cross-site authentication request denied.")


def set_auth_cookie(response, name, value, lifetime):
    response.set_cookie(
        name, value, max_age=lifetime, path="/",
        secure=True, httponly=True, samesite="strict",
    )


@dataclass
class AuthenticatedSession:
    token_digest: str
    csrf_token: str
    user: dict


def find_session(request: Request, db: Session, now: float):
    token = request.cookies.get(SESSION_COOKIE, "")
    if not TOKEN_PATTERN.fullmatch(token):
        return None
    key = digest(token)
    row = db.execute(select(sessions).where(sessions.c.token_digest == key)).mappings().first()
    if row is None:
        return None
    if now >= row["expires_at"]:
        db.execute(delete(sessions).where(sessions.c.token_digest == key))
        db.commit()
        return None
    user = db.execute(select(users).where(users.c.id == row["user_id"])).mappings().first()
    if user is None or not user["is_active"]:
        return None
    return AuthenticatedSession(key, row["csrf_token"], dict(user))


def current_session(
    request: Request, db: Session = Depends(get_db), now: float = Depends(now_seconds),
):
    require_https(request)
    session = find_session(request, db, now)
    if session is None:
        raise HTTPException(401, "Authentication required.")
    return session


def csrf_session(request: Request, session=Depends(current_session)):
    check_request_origin(request)
    supplied = request.headers.get("x-csrf-token", "")
    if not TOKEN_PATTERN.fullmatch(supplied) or not secrets.compare_digest(supplied, session.csrf_token):
        raise HTTPException(403, "Invalid CSRF token.")
    return session
