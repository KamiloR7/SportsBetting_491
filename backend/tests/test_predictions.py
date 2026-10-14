import os
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import HTTPException
from sqlalchemy.exc import OperationalError

# Provide test database settings so backend modules can be imported
# without requiring local PostgreSQL credentials.
os.environ.setdefault("DATABASE_HOST", "localhost")
os.environ.setdefault("DATABASE_PORT", "5432")
os.environ.setdefault("DATABASE_NAME", "test_db")
os.environ.setdefault("DATABASE_USER", "test_user")
os.environ.setdefault("DATABASE_PASSWORD", "test_password")

from app.routes.predictions import run_match_prediction


class TestPredictionEndpoint(unittest.TestCase):

    def test_returns_latest_prediction_for_match(self):
        db = MagicMock()
        result = MagicMock()
        result.first.return_value = SimpleNamespace(
            match_id=7,
            model_version_id=2,
            model_name="baseline",
            model_version="v1",
            predicted_winner_id=10,
            predicted_winner_name="Home Team",
            home_win_probability=0.62,
            away_win_probability=0.38,
            confidence=0.62,
            generated_at=datetime(2026, 10, 14, 12, 0),
        )
        db.execute.return_value = result

        prediction = run_match_prediction(match_id=7, db=db)

        self.assertEqual(prediction.match_id, 7)
        self.assertEqual(prediction.predicted_winner_name, "Home Team")
        self.assertEqual(prediction.home_win_probability, 0.62)

    def test_missing_prediction_returns_404(self):
        db = MagicMock()
        result = MagicMock()
        result.first.return_value = None
        db.execute.return_value = result

        with self.assertRaises(HTTPException) as context:
            run_match_prediction(match_id=7, db=db)

        self.assertEqual(context.exception.status_code, 404)

    def test_unavailable_database_returns_503(self):
        db = MagicMock()
        db.execute.side_effect = OperationalError(
            "SELECT prediction",
            {},
            RuntimeError("database unavailable"),
        )

        with self.assertRaises(HTTPException) as context:
            run_match_prediction(match_id=7, db=db)

        self.assertEqual(context.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
