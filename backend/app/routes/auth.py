from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.core.passwords import hash_password
from app.core.authentication import require_https
from app.schemas.auth import UserOut, UserRegister

router = APIRouter(prefix="/auth", tags=["auth"])


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
        raise HTTPException(status_code=409, detail="An account with these details already exists.") from None


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
