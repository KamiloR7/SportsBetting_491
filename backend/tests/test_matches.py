import os
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import HTTPException

# Provide test database settings so backend modules can be imported
# without requiring local PostgreSQL credentials.
os.environ.setdefault("DATABASE_HOST", "localhost")
os.environ.setdefault("DATABASE_PORT", "5432")
os.environ.setdefault("DATABASE_NAME", "test_db")
os.environ.setdefault("DATABASE_USER", "test_user")
os.environ.setdefault("DATABASE_PASSWORD", "test_password")

from app.routes.matches import get_match, list_matches, match_history


def sample_match(
    match_id=1,
    status="scheduled",
):
    return SimpleNamespace(
        id=match_id,
        league_id=1,
        league_name="NFL",
        home_team_id=10,
        home_team_name="Home Team",
        away_team_id=20,
        away_team_name="Away Team",
        start_time=datetime(2026, 10, 1, 18, 0),
        status=status,
        home_score=None if status != "final" else 24,
        away_score=None if status != "final" else 17,
        neutral_site=False,
    )


class TestMatchEndpoints(unittest.TestCase):

    def test_list_matches_returns_matches(self):
        db = MagicMock()

        result = MagicMock()
        result.all.return_value = [
            sample_match(1),
            sample_match(2),
        ]

        db.execute.return_value = result

        matches = list_matches(
            league_id=None,
            status=None,
            db=db,
        )

        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0].id, 1)
        self.assertEqual(matches[0].league_name, "NFL")

    def test_match_history_returns_completed_matches(self):
        db = MagicMock()

        result = MagicMock()
        result.all.return_value = [
            sample_match(
                match_id=3,
                status="final",
            )
        ]

        db.execute.return_value = result

        matches = match_history(
            league_id=None,
            limit=100,
            db=db,
        )

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].status, "final")
        self.assertEqual(matches[0].home_score, 24)
        self.assertEqual(matches[0].away_score, 17)

    def test_get_match_returns_match(self):
        db = MagicMock()

        result = MagicMock()
        result.first.return_value = sample_match(5)

        db.execute.return_value = result

        match = get_match(
            match_id=5,
            db=db,
        )

        self.assertEqual(match.id, 5)
        self.assertEqual(
            match.home_team_name,
            "Home Team",
        )
        self.assertEqual(
            match.away_team_name,
            "Away Team",
        )

    def test_get_match_not_found_returns_404(self):
        db = MagicMock()

        result = MagicMock()
        result.first.return_value = None

        db.execute.return_value = result

        with self.assertRaises(HTTPException) as context:
            get_match(
                match_id=999,
                db=db,
            )

        self.assertEqual(
            context.exception.status_code,
            404,
        )


if __name__ == "__main__":
    unittest.main()