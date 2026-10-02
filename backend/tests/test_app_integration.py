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
        }

        for route in expected_routes:
            self.assertIn(route, paths)


if __name__ == "__main__":
    unittest.main()