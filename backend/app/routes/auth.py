import bcrypt

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.authentication import require_https
from app.core.passwords import hash_password
from app.database.db import get_db
from app.schemas.auth import UserLogin, UserOut, UserRegister
from app.services.login_throttle import (
    clear_failures,
    is_blocked,
    record_failure,
)
from app.services.password_security import verify_password
from app.services.session_security import (
    create_csrf_token,
    create_session,
    get_session_user,
    revoke_session,
    validate_csrf_token,
)


DUMMY_PASSWORD_HASH = bcrypt.hashpw(
    b"dummy-password-for-timing-protection",
    bcrypt.gensalt(),
).decode("utf-8")


router = APIRouter(prefix="/auth", tags=["auth"])


# ============================================================
# Registration
# ============================================================

@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_https)],
)
def register_user(user: UserRegister, db: Session = Depends(get_db)):
    email = str(user.email).casefold()

    existing_email = db.execute(
        text("SELECT id FROM users WHERE lower(email) = :email"),
        {"email": email},
    ).first()

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    if user.username:
        existing_username = db.execute(
            text("SELECT id FROM users WHERE username = :username"),
            {"username": user.username},
        ).first()

        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this username already exists.",
            )

    password_hash = hash_password(user.password)

    try:
        return _insert_user(user, email, password_hash, db)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with these details already exists.",
        ) from None


def _insert_user(user, email, password_hash, db):
    result = db.execute(
        text(
            """
            INSERT INTO users (
                email,
                username,
                display_name,
                password_hash
            )
            VALUES (
                :email,
                :username,
                :display_name,
                :password_hash
            )
            RETURNING
                id,
                email,
                username,
                display_name,
                is_active,
                created_at
            """
        ),
        {
            "email": email,
            "username": user.username,
            "display_name": user.display_name,
            "password_hash": password_hash,
        },
    ).first()

    db.commit()

    return UserOut(
        id=result.id,
        email=result.email,
        username=result.username,
        display_name=result.display_name,
        is_active=result.is_active,
        created_at=result.created_at,
    )


# ============================================================
# Sprint 4 — Secure Login
# Jira: SCRUM-187, SCRUM-188
# ============================================================

@router.post(
    "/login",
    dependencies=[Depends(require_https)],
)
def login_user(
    credentials: UserLogin,
    response: Response,
    db: Session = Depends(get_db),
):
    """Verify credentials and create a 30-minute session."""

    throttle_key = str(credentials.email).casefold()

    if is_blocked(throttle_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
        )

    user = db.execute(
        text(
            """
            SELECT id, email, password_hash, is_active
            FROM users
            WHERE lower(email) = :email
            """
        ),
        {"email": throttle_key},
    ).first()

    stored_hash = (
        user.password_hash
        if user is not None and user.is_active
        else DUMMY_PASSWORD_HASH
    )

    password_valid = verify_password(
        credentials.password,
        stored_hash,
    )

    if user is None or not user.is_active or not password_valid:
        record_failure(throttle_key)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    clear_failures(throttle_key)

    session_token = create_session(user.id)

    response.set_cookie(
        key="vigor_session",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=30 * 60,
        path="/",
    )

    return {
        "message": "Login successful",
        "user_id": user.id,
    }


# ============================================================
# Sprint 4 — Protected Current User
# Jira: SCRUM-187
# ============================================================

@router.get("/me")
def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
):
    """Return user information only for a valid session."""

    session_token = request.cookies.get("vigor_session")
    user_id = get_session_user(session_token)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    user = db.execute(
        text(
            """
            SELECT id, email, username, display_name, is_active
            FROM users
            WHERE id = :user_id
            """
        ),
        {"user_id": user_id},
    ).first()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "display_name": user.display_name,
    }


# ============================================================
# Sprint 4 — Logout with CSRF Protection
# Jira: SCRUM-187, SCRUM-188
# ============================================================

@router.post("/logout")
def logout_user(
    request: Request,
    response: Response,
):
    """Revoke a session only after successful CSRF validation."""

    session_token = request.cookies.get("vigor_session")

    if get_session_user(session_token) is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    csrf_token = request.headers.get("X-CSRF-Token")

    if not validate_csrf_token(session_token, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token",
        )

    revoke_session(session_token)

    response.delete_cookie(
        key="vigor_session",
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )

    return {"message": "Logout successful"}


# ============================================================
# Sprint 4 — CSRF Token Endpoint
# Jira: SCRUM-188
# ============================================================

@router.get("/csrf")
def get_csrf_token(request: Request):
    """Issue a CSRF token for an authenticated session."""

    session_token = request.cookies.get("vigor_session")
    csrf_token = create_csrf_token(session_token)

    if csrf_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    return {"csrf_token": csrf_token}