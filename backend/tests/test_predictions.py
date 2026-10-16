import os
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
from fastapi import HTTPException
from sqlalchemy.exc import OperationalError

os.environ.setdefault("DATABASE_HOST", "localhost")
os.environ.setdefault("DATABASE_PORT", "5432")
os.environ.setdefault("DATABASE_NAME", "test_db")
os.environ.setdefault("DATABASE_USER", "test_user")
os.environ.setdefault("DATABASE_PASSWORD", "test_password")

from app.routes.predictions import run_match_prediction
from app.services.match_prediction import predict_probabilities, team_features


def scheduled_match(sport="NFL", status="scheduled"):
    return SimpleNamespace(
        id=7,
        league_id=2,
        sport=sport,
        home_team_id=10,
        home_team_name="Home Team",
        away_team_id=20,
        away_team_name="Away Team",
        start_time=datetime(2026, 10, 20, 18, 0, tzinfo=timezone.utc),
        status=status,
    )


def final_match(home_id=10, away_id=20, home_score=3, away_score=1):
    return SimpleNamespace(
        home_team_id=home_id,
        away_team_id=away_id,
        home_score=home_score,
        away_score=away_score,
    )


def mock_db(match=None, history=None):
    db = MagicMock()
    match_result = MagicMock()
    match_result.first.return_value = match
    history_result = MagicMock()
    history_result.all.return_value = history or []
    db.execute.side_effect = [match_result, history_result]
    return db


class FakeBinaryModel:
    classes_ = [0, 1]

    def predict_proba(self, features):
        return np.array([[0.4, 0.6]])

    def predict(self, features):
        return [1]


class TestPredictionEndpoint(unittest.TestCase):
    def test_runs_prediction_for_scheduled_match(self):
        db = mock_db(scheduled_match(), [final_match()])
        result = {
            "predicted_outcome": "home_win",
            "home_win_probability": 0.6,
            "away_win_probability": 0.4,
            "draw_probability": None,
            "confidence": 0.6,
            "model_version": "v1",
        }
        with patch("app.routes.predictions.predict_probabilities", return_value=result) as predict:
            prediction = run_match_prediction(match_id=7, db=db)

        self.assertEqual(prediction.predicted_winner_name, "Home Team")
        self.assertEqual(prediction.home_win_probability, 0.6)
        self.assertEqual(predict.call_args.args[:3], ("NFL", 10, 20))
        self.assertEqual(db.execute.call_args.args[1]["league_id"], 2)

    def test_draw_has_no_predicted_winner(self):
        db = mock_db(scheduled_match("EPL"), [final_match(10, 20, 1, 1)])
        result = {
            "predicted_outcome": "draw",
            "home_win_probability": 0.3,
            "away_win_probability": 0.3,
            "draw_probability": 0.4,
            "confidence": 0.4,
            "model_version": "v1",
        }
        with patch("app.routes.predictions.predict_probabilities", return_value=result):
            prediction = run_match_prediction(match_id=7, db=db)
        self.assertIsNone(prediction.predicted_winner_id)
        self.assertEqual(prediction.predicted_outcome, "draw")

    def test_missing_match_returns_404(self):
        with self.assertRaises(HTTPException) as context:
            run_match_prediction(match_id=7, db=mock_db())
        self.assertEqual(context.exception.status_code, 404)

    def test_completed_match_returns_422(self):
        with self.assertRaises(HTTPException) as context:
            run_match_prediction(match_id=7, db=mock_db(scheduled_match(status="final")))
        self.assertEqual(context.exception.status_code, 422)

    def test_unavailable_database_returns_503(self):
        db = MagicMock()
        db.execute.side_effect = OperationalError("SELECT match", {}, RuntimeError("unavailable"))
        with self.assertRaises(HTTPException) as context:
            run_match_prediction(match_id=7, db=db)
        self.assertEqual(context.exception.status_code, 503)

    def test_missing_model_returns_503(self):
        with patch("app.routes.predictions.predict_probabilities", side_effect=RuntimeError("No model")):
            with self.assertRaises(HTTPException) as context:
                run_match_prediction(match_id=7, db=mock_db(scheduled_match(), [final_match()]))
        self.assertEqual(context.exception.status_code, 503)


class TestPredictionFeatures(unittest.TestCase):
    def test_team_features_use_both_home_and_away_history(self):
        history = [final_match(10, 20, 3, 1), final_match(20, 10, 2, 2)]
        self.assertEqual(team_features(10, history), (0.5, 2.5, 1.5, 2))

    def test_binary_prediction_runs_existing_model(self):
        history = [final_match()]
        with patch("app.services.match_prediction.model_artifact", return_value="model.pkl"):
            with patch("app.services.match_prediction.load_trusted_baseline", return_value=(FakeBinaryModel(), {"sport": "NFL", "artifact_version": "v1"})):
                result = predict_probabilities("NFL", 10, 20, history)
        self.assertEqual(result["predicted_outcome"], "home_win")
        self.assertAlmostEqual(result["home_win_probability"], 0.6)
        self.assertIsNone(result["draw_probability"])

    def test_epl_prediction_includes_draw_probability(self):
        history = [final_match(10, 20, 1, 1), final_match(20, 10, 2, 0)]
        with patch("app.services.match_prediction.model_artifact", return_value="model.pkl"):
            with patch("app.services.match_prediction.load_trusted_baseline", return_value=(FakeBinaryModel(), {"sport": "EPL"})):
                result = predict_probabilities("EPL", 10, 20, history)
        self.assertAlmostEqual(sum(result[key] for key in ("home_win_probability", "away_win_probability", "draw_probability")), 1.0)
        self.assertGreater(result["draw_probability"], 0)

    def test_requires_history_for_both_teams(self):
        with self.assertRaisesRegex(ValueError, "Both teams need"):
            predict_probabilities("NFL", 10, 20, [final_match(10, 30)])


if __name__ == "__main__":
    unittest.main()
