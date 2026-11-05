"""Shared bcrypt verifier; never silently truncate bcrypt's 72-byte input limit."""

import bcrypt


def password_bytes(password: str) -> bytes:
    value = password.encode("utf-8")
    if len(value) > 72:
        raise ValueError("Password must be at most 72 UTF-8 bytes.")
    return value


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password_bytes(password), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password_bytes(password), stored_hash.encode("ascii"))
    except (ValueError, UnicodeError):
        return False
