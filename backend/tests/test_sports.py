import os
import unittest
from unittest.mock import MagicMock

from sqlalchemy.exc import OperationalError

# Provide test database settings so backend modules can be imported
# without requiring local PostgreSQL credentials.
os.environ.setdefault("DATABASE_HOST", "localhost")
os.environ.setdefault("DATABASE_PORT", "5432")
os.environ.setdefault("DATABASE_NAME", "test_db")
os.environ.setdefault("DATABASE_USER", "test_user")
os.environ.setdefault("DATABASE_PASSWORD", "test_password")

from app.routes.sports import list_leagues, list_sports, list_teams


def unavailable_db():
    db = MagicMock()
    db.execute.side_effect = OperationalError(
        "SELECT reference data",
        {},
        RuntimeError("database unavailable"),
    )
    return db


class TestSportsFallbacks(unittest.TestCase):

    def test_sports_fallback_uses_seed_reference_data(self):
        sports = list_sports(db=unavailable_db())

        self.assertIn(
            "Basketball",
            {sport.name for sport in sports},
        )

    def test_leagues_fallback_includes_sprint3_ui_scope(self):
        leagues = list_leagues(db=unavailable_db())

        self.assertTrue(
            {"NFL", "MLB", "EPL"}.issubset(
                {league.abbreviation for league in leagues}
            )
        )

    def test_teams_fallback_includes_sport_summary(self):
        teams = list_teams(db=unavailable_db())

        lakers = next(team for team in teams if team.abbreviation == "LAL")

        self.assertEqual(lakers.sport.slug, "basketball")


if __name__ == "__main__":
    unittest.main()
