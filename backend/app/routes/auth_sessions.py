"""Sprint 4 authentication prototype; all users/data in assessment are synthetic."""

import logging
import math
import secrets

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response
from sqlalchemy import delete, func, insert, select, text, update
from sqlalchemy.orm import Session

from app.core.authentication import (
    BLOCK_SECONDS, CHALLENGE_COOKIE, SESSION_COOKIE, SESSION_SECONDS,
    TOKEN_PATTERN, WINDOW_SECONDS, check_request_origin, csrf_session,
    current_session, digest, find_session, now_seconds, require_https, set_auth_cookie,
)
from app.core.config import settings
from app.core.passwords import hash_password, verify_password
from app.database.auth_tables import assessment_records, attempts, challenges, sessions, users
from app.database.db import get_db
from app.schemas.auth import AssessmentNote, UserLogin, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("vigor.security")
# Equal bcrypt work for a nonexistent user; no raw user input goes into logs.
DUMMY_HASH = hash_password(secrets.token_urlsafe(32))


@router.get("/csrf")
def csrf_token(request: Request, response: Response, db: Session = Depends(get_db), now: float = Depends(now_seconds)):
    check_request_origin(request)
    response.headers["Cache-Control"] = "no-store"
    existing = find_session(request, db, now)
    if existing:
        return {"csrf_token": existing.csrf_token}
    nonce, token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    db.execute(delete(challenges).where(challenges.c.expires_at <= now))
    db.execute(insert(challenges).values(nonce_digest=digest(nonce), csrf_token=token, expires_at=now + WINDOW_SECONDS))
    db.commit()
    set_auth_cookie(response, CHALLENGE_COOKIE, nonce, WINDOW_SECONDS)
    return {"csrf_token": token}


def check_login_csrf(request, db, now):
    check_request_origin(request)
    nonce = request.cookies.get(CHALLENGE_COOKIE, "")
    supplied = request.headers.get("x-csrf-token", "")
    if not TOKEN_PATTERN.fullmatch(nonce) or not TOKEN_PATTERN.fullmatch(supplied):
        raise HTTPException(403, "Invalid CSRF token.")
    row = db.execute(select(challenges).where(challenges.c.nonce_digest == digest(nonce))).mappings().first()
    if row is None or now >= row["expires_at"] or not secrets.compare_digest(supplied, row["csrf_token"]):
        raise HTTPException(403, "Invalid CSRF token.")


@router.post("/login", response_model=UserOut)
def login(user: UserLogin, request: Request, response: Response, db: Session = Depends(get_db), now: float = Depends(now_seconds)):
    check_login_csrf(request, db, now)
    # Account-wide key, deliberately independent of spoofable X-Forwarded-For.
    email = str(user.email).casefold()
    key = digest(email)
    db.execute(text("""INSERT INTO auth_login_attempts
        (key_digest, window_start, failure_count, blocked_until, failure_times)
        VALUES (:key, :now, 0, 0, '[]') ON CONFLICT (key_digest) DO NOTHING"""), {"key": key, "now": now})
    throttle = db.execute(select(attempts).where(attempts.c.key_digest == key).with_for_update()).mappings().one()
    if throttle["blocked_until"] > now:
        retry = str(math.ceil(throttle["blocked_until"] - now))
        db.commit()
        logger.info("event=login_blocked")
        raise HTTPException(429, "Login temporarily unavailable. Try again later.", headers={"Retry-After": retry})
    recent = [stamp for stamp in throttle["failure_times"] if 0 <= now - stamp < WINDOW_SECONDS]
    accounts = db.execute(select(users).where(func.lower(users.c.email) == email)).mappings().all()
    # Fail closed for ambiguous legacy email casing rather than choose an identity.
    account = accounts[0] if len(accounts) == 1 else None
    valid = verify_password(user.password, account["password_hash"] if account else DUMMY_HASH)
    if not valid or account is None or not account["is_active"]:
        recent.append(now)
        count = len(recent)
        db.execute(update(attempts).where(attempts.c.key_digest == key).values(
            window_start=recent[0], failure_count=count, failure_times=recent,
            blocked_until=now + BLOCK_SECONDS if count >= 5 else 0,
        ))
        db.commit()
        logger.info("event=login_failed")
        raise HTTPException(401, "Invalid email or password.")
    db.execute(update(attempts).where(attempts.c.key_digest == key).values(
        window_start=now, failure_count=0, blocked_until=0, failure_times=[],
    ))
    # Never retain a client-supplied session (session fixation).
    previous = request.cookies.get(SESSION_COOKIE, "")
    if TOKEN_PATTERN.fullmatch(previous):
        db.execute(delete(sessions).where(sessions.c.token_digest == digest(previous)))
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    db.execute(delete(sessions).where(sessions.c.expires_at <= now))
    db.execute(insert(sessions).values(token_digest=digest(token), user_id=account["id"], csrf_token=csrf, expires_at=now + SESSION_SECONDS))
    db.execute(delete(challenges).where(challenges.c.nonce_digest == digest(request.cookies[CHALLENGE_COOKIE])))
    db.commit()
    set_auth_cookie(response, SESSION_COOKIE, token, SESSION_SECONDS)
    response.delete_cookie(CHALLENGE_COOKIE, path="/", secure=not settings.LOCAL_DEMO_HTTP, httponly=True, samesite="strict")
    response.headers["Cache-Control"] = "no-store"
    logger.info("event=login_succeeded")
    return account


@router.get("/me", response_model=UserOut)
def me(response: Response, session=Depends(current_session)):
    response.headers["Cache-Control"] = "no-store"
    return session.user


@router.post("/logout", status_code=204)
def logout(response: Response, session=Depends(csrf_session), db: Session = Depends(get_db)):
    db.execute(delete(sessions).where(sessions.c.token_digest == session.token_digest))
    db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/", secure=not settings.LOCAL_DEMO_HTTP, httponly=True, samesite="strict")
    response.headers["Cache-Control"] = "no-store"
    logger.info("event=logout_succeeded")


def assessment_enabled():
    if not settings.AUTH_ASSESSMENT_ENABLED:
        raise HTTPException(404, "Not found.")


def owned_record(record_id, session, db):
    row = db.execute(select(assessment_records).where(assessment_records.c.id == record_id)).mappings().first()
    if row is None:
        raise HTTPException(404, "Assessment record not found.")
    if row["owner_id"] != session.user["id"]:
        logger.info("event=assessment_access_denied")
        raise HTTPException(403, "Permission denied.")
    return row


@router.get("/assessment/records/{record_id}", dependencies=[Depends(assessment_enabled)])
def read_assessment_record(response: Response, record_id: int = Path(ge=1), session=Depends(current_session), db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return dict(owned_record(record_id, session, db))


@router.patch("/assessment/records/{record_id}", dependencies=[Depends(assessment_enabled)])
def write_assessment_record(note: AssessmentNote, response: Response, record_id: int = Path(ge=1), session=Depends(csrf_session), db: Session = Depends(get_db)):
    owned_record(record_id, session, db)
    db.execute(update(assessment_records).where(assessment_records.c.id == record_id, assessment_records.c.owner_id == session.user["id"]).values(note=note.note))
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return {"id": record_id, "owner_id": session.user["id"], "note": note.note}
