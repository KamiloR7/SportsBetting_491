from datetime import datetime, timedelta, timezone

from app.services import session_security


def test_session_creation():
    token = session_security.create_session(1)

    assert isinstance(token, str)
    assert session_security.get_session_user(token) == 1

    session_security.revoke_session(token)


def test_invalid_session_rejected():
    assert (
        session_security.get_session_user("invalid-token")
        is None
    )


def test_logout_revokes_session():
    token = session_security.create_session(1)

    session_security.revoke_session(token)

    assert session_security.get_session_user(token) is None


def test_expired_session_rejected():
    token = session_security.create_session(1)
    token_key = session_security._token_hash(token)

    with session_security._lock:
        session_security._sessions[token_key][
            "expires_at"
        ] = datetime.now(timezone.utc) - timedelta(
            seconds=1
        )

    assert session_security.get_session_user(token) is None

from unittest.mock import patch


def test_session_expires_at_30_minutes():
    start = datetime(
        2026, 11, 5, 12, 0, 0,
        tzinfo=timezone.utc,
    )

    with patch.object(session_security, "datetime") as clock:
        clock.now.return_value = start

        token = session_security.create_session(1)

        clock.now.return_value = start + timedelta(
            minutes=29,
            seconds=59,
        )
        assert session_security.get_session_user(token) == 1

        clock.now.return_value = start + timedelta(
            minutes=30
        )
        assert session_security.get_session_user(token) is None