import bcrypt


def verify_password(
    plain_password: str,
    stored_hash: str,
) -> bool:
    """Verify a password against a stored bcrypt hash."""

    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            stored_hash.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False