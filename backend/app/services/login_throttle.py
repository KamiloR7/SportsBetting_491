import threading
import time

from collections import defaultdict, deque

MAX_FAILURES = 5
WINDOW_SECONDS = 5 * 60
BLOCK_SECONDS = 15 * 60

_lock = threading.Lock()
_failures = defaultdict(deque)
_blocked_until = {}


def is_blocked(key: str) -> bool:
    """Check whether login attempts are temporarily blocked."""
    now = time.monotonic()

    with _lock:
        blocked_until = _blocked_until.get(key)

        if blocked_until is None:
            return False

        if now >= blocked_until:
            _blocked_until.pop(key, None)
            _failures.pop(key, None)
            return False

        return True


def record_failure(key: str) -> None:
    """Record a failed login within the rolling 5-minute window."""
    now = time.monotonic()

    with _lock:
        attempts = _failures[key]

        while attempts and now - attempts[0] >= WINDOW_SECONDS:
            attempts.popleft()

        attempts.append(now)

        if len(attempts) >= MAX_FAILURES:
            _blocked_until[key] = now + BLOCK_SECONDS


def clear_failures(key: str) -> None:
    """Reset attempts after a successful login."""
    with _lock:
        _failures.pop(key, None)
        _blocked_until.pop(key, None)