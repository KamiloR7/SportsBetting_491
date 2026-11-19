import os
import unittest

os.environ.setdefault("DATABASE_HOST", "localhost")
os.environ.setdefault("DATABASE_PORT", "5432")
os.environ.setdefault("DATABASE_NAME", "test_db")
os.environ.setdefault("DATABASE_USER", "test_user")
os.environ.setdefault("DATABASE_PASSWORD", "test_password")

from app.main import app


class TestBackendIntegration(unittest.TestCase):

    def test_expected_routes_are_registered(self):
        paths = set(app.openapi()["paths"].keys())

        expected_routes = {
            "/health",
            "/sports",
            "/leagues",
            "/teams",
            "/auth/register",
            "/matches",
            "/matches/history",
            "/matches/{match_id}",
            "/predictions",
            "/predictions/matches/{match_id}",
        }

        for route in expected_routes:
            self.assertIn(route, paths)

    def test_route_access_inventory_matches_public_api(self):
        schema = app.openapi()
        expected_public_operations = {
            ("get", "/health"),
            ("get", "/sports"),
            ("get", "/leagues"),
            ("get", "/teams"),
            ("post", "/auth/register"),
            ("get", "/matches"),
            ("get", "/matches/history"),
            ("get", "/matches/{match_id}"),
            ("post", "/predictions"),
            ("post", "/predictions/matches/{match_id}"),
        }
        actual_operations = {
            (method, path)
            for path, operations in schema["paths"].items()
            for method in operations
            if method in {"get", "post", "put", "patch", "delete"}
        }

        self.assertEqual(actual_operations, expected_public_operations)
        self.assertNotIn("security", schema)
        for path, operations in schema["paths"].items():
            for method, operation in operations.items():
                if method in {"get", "post", "put", "patch", "delete"}:
                    self.assertNotIn("security", operation, f"{method.upper()} {path}")


if __name__ == "__main__":
    unittest.main()
