import hashlib
import secrets
import threading

from datetime import datetime, timedelta, timezone

SESSION_MINUTES = 30

# Development prototype only.
# Replace with shared persistent storage before deployment.
_sessions = {}
_lock = threading.Lock()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(user_id: int) -> str:
    """Create an unpredictable session token."""

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=SESSION_MINUTES
    )

    with _lock:
        _sessions[_token_hash(token)] = {
            "user_id": user_id,
            "expires_at": expires_at,
        }

    return token


def get_session_user(token: str | None) -> int | None:
    """Return the user ID if the session is still valid."""

    if not token:
        return None

    token_key = _token_hash(token)

    with _lock:
        session = _sessions.get(token_key)

        if session is None:
            return None

        if datetime.now(timezone.utc) >= session["expires_at"]:
            _sessions.pop(token_key, None)
            return None

        return session["user_id"]


def revoke_session(token: str | None) -> None:
    """Invalidate a session immediately."""

    if not token:
        return

    with _lock:
        _sessions.pop(_token_hash(token), None)

def create_csrf_token(session_token: str) -> str | None:
    """Create a CSRF token associated with an active session."""
    user_id = get_session_user(session_token)

    if user_id is None:
        return None

    csrf_token = secrets.token_urlsafe(32)

    with _lock:
        session = _sessions.get(
            _token_hash(session_token)
        )

        if session is None:
            return None

        session["csrf_token_hash"] = _token_hash(
            csrf_token
        )

    return csrf_token


def validate_csrf_token(
    session_token: str | None,
    csrf_token: str | None,
) -> bool:
    """Validate a CSRF token against its session."""

    if not session_token or not csrf_token:
        return False

    if get_session_user(session_token) is None:
        return False

    with _lock:
        session = _sessions.get(
            _token_hash(session_token)
        )

        if session is None:
            return False

        expected_hash = session.get("csrf_token_hash")

    if expected_hash is None:
        return False

    return secrets.compare_digest(
        expected_hash,
        _token_hash(csrf_token),
    )

def create_csrf_token(session_token: str | None) -> str | None:
    """Create a CSRF token for an active authenticated session."""
    if not session_token:
        return None

    if get_session_user(session_token) is None:
        return None

    csrf_token = secrets.token_urlsafe(32)

    with _lock:
        session = _sessions.get(_token_hash(session_token))

        if session is None:
            return None

        session["csrf_token_hash"] = _token_hash(csrf_token)

    return csrf_token


def validate_csrf_token(
    session_token: str | None,
    csrf_token: str | None,
) -> bool:
    """Validate a CSRF token bound to the active session."""
    if not session_token or not csrf_token:
        return False

    if get_session_user(session_token) is None:
        return False

    with _lock:
        session = _sessions.get(_token_hash(session_token))

        if session is None:
            return False

        expected_hash = session.get("csrf_token_hash")

    if expected_hash is None:
        return False

    return secrets.compare_digest(
        expected_hash,
        _token_hash(csrf_token),
    )