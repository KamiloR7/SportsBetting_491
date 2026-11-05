"""Fail when a route is unclassified or a protected policy lacks enforcement/tests."""

import os

for name, value in {"DATABASE_HOST": "localhost", "DATABASE_PORT": "5432",
                    "DATABASE_NAME": "test_db", "DATABASE_USER": "test_user",
                    "DATABASE_PASSWORD": "test_password"}.items():
    os.environ.setdefault(name, value)

from fastapi import FastAPI
from fastapi.routing import APIRoute, iter_route_contexts
import pytest

from app.core.authentication import csrf_session, current_session
from app.main import app
from app.security_assessment import PROTECTED, route_inventory
from backend.tests.test_auth_security import PROTECTED as TEST_CASES


def dependency_calls(dependant):
    for child in dependant.dependencies:
        yield child.call
        yield from dependency_calls(child)


def test_every_runtime_route_has_explicit_access_policy():
    inventory = route_inventory(app)
    assert {(row["method"], row["path"]) for row in inventory if row["access"] == "protected"} == set(PROTECTED)
    covered = {(method, path.replace("/records/1", "/records/{record_id}")) for method, path, _ in TEST_CASES}
    assert covered == set(PROTECTED), "Every protected policy needs a denial/zero-write test"
    for route in iter_route_contexts(app.routes):
        if not isinstance(route.original_route, APIRoute):
            continue
        for method in route.methods:
            calls = set(dependency_calls(route.dependant))
            if (method, route.path) in PROTECTED:
                assert current_session in calls
                if method in {"POST", "PATCH"}:
                    assert csrf_session in calls


def test_new_unclassified_route_fails_inventory():
    other = FastAPI()

    @other.get("/unclassified-private-feature")
    def private_feature():
        return {}

    with pytest.raises(ValueError, match="lacks an approved access policy"):
        route_inventory(other)
