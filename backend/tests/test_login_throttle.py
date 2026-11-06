from unittest.mock import patch

from app.services import login_throttle


def test_five_failures_trigger_lockout():
    key = "lockout-test@example.com"
    login_throttle.clear_failures(key)

    try:
        for _ in range(4):
            login_throttle.record_failure(key)
            assert not login_throttle.is_blocked(key)

        login_throttle.record_failure(key)

        assert login_throttle.is_blocked(key)
    finally:
        login_throttle.clear_failures(key)


def test_successful_login_resets_failure_count():
    key = "reset-test@example.com"
    login_throttle.clear_failures(key)

    try:
        login_throttle.record_failure(key)
        login_throttle.record_failure(key)

        login_throttle.clear_failures(key)

        assert not login_throttle.is_blocked(key)
    finally:
        login_throttle.clear_failures(key)


def test_lockout_expires_after_fifteen_minutes():
    key = "expiry-test@example.com"
    login_throttle.clear_failures(key)

    try:
        with patch.object(
            login_throttle.time,
            "monotonic",
            return_value=1000,
        ):
            for _ in range(5):
                login_throttle.record_failure(key)

            assert login_throttle.is_blocked(key)

        with patch.object(
            login_throttle.time,
            "monotonic",
            return_value=1899,
        ):
            assert login_throttle.is_blocked(key)

        with patch.object(
            login_throttle.time,
            "monotonic",
            return_value=1900,
        ):
            assert not login_throttle.is_blocked(key)
    finally:
        login_throttle.clear_failures(key)


def test_old_failures_fall_outside_window():
    key = "window-test@example.com"
    login_throttle.clear_failures(key)

    try:
        with patch.object(
            login_throttle.time,
            "monotonic",
            return_value=1000,
        ):
            for _ in range(4):
                login_throttle.record_failure(key)

        with patch.object(
            login_throttle.time,
            "monotonic",
            return_value=1301,
        ):
            login_throttle.record_failure(key)

            assert not login_throttle.is_blocked(key)
    finally:
        login_throttle.clear_failures(key)