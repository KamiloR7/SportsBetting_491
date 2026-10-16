"""QA guard: fail if regression tests attempt network or PostgreSQL access."""
import sys

import psycopg2


def deny_postgres(*args, **kwargs):
    raise AssertionError("SCRUM-203: PostgreSQL connections prohibited")


def audit(event, args):
    if event in {"socket.connect", "socket.connect_ex", "socket.getaddrinfo"}:
        raise AssertionError("SCRUM-203: network access prohibited")


psycopg2.connect = deny_postgres
sys.addaudithook(audit)
