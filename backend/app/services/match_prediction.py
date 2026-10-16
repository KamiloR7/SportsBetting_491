"""Build pre-match team features and run the locally trained baseline."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from app.ml.predict_multisport import load_trusted_baseline, predict_outcomes

DEFAULT_MODEL_DIR = Path(__file__).resolve().parents[3] / "build" / "sprint2-models"


def model_artifact(sport: str) -> Path:
    root = Path(os.environ.get("PREDICTION_MODEL_DIR", DEFAULT_MODEL_DIR))
    name = sport.lower()
    candidates = list(root.glob(f"{name}-*/{name}_baseline.pkl"))
    if not candidates:
        raise FileNotFoundError(f"No trained {sport} model is available.")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def team_features(team_id: int, history: list) -> tuple[float, float, float, int]:
    scored = []
    allowed = []
    wins = 0
    for match in history:
        if match.home_team_id == team_id:
            team_score, opponent_score = match.home_score, match.away_score
        elif match.away_team_id == team_id:
            team_score, opponent_score = match.away_score, match.home_score
        else:
            continue
        scored.append(team_score)
        allowed.append(opponent_score)
        wins += team_score > opponent_score

    count = len(scored)
    if not count:
        return 0.0, 0.0, 0.0, 0
    return wins / count, sum(scored) / count, sum(allowed) / count, count


def predict_probabilities(sport: str, home_team_id: int, away_team_id: int, history: list) -> dict:
    home_rate, home_score, home_allowed, home_games = team_features(home_team_id, history)
    away_rate, away_score, away_allowed, away_games = team_features(away_team_id, history)
    if not home_games or not away_games:
        raise ValueError("Both teams need a completed match before a prediction can run.")

    features = pd.DataFrame([{
        "home_win_rate": home_rate,
        "away_win_rate": away_rate,
        "home_avg_score": home_score,
        "away_avg_score": away_score,
        "home_avg_allowed": home_allowed,
        "away_avg_allowed": away_allowed,
    }])
    try:
        model, metadata = load_trusted_baseline(model_artifact(sport))
    except (OSError, ValueError) as exc:
        raise RuntimeError("A trained prediction model is unavailable.") from exc
    if metadata.get("sport") != sport:
        raise RuntimeError("The model artifact does not match the selected league.")

    try:
        home_probability = float(predict_outcomes(model, features).iloc[0]["probability_home_win"])
    except ValueError as exc:
        raise RuntimeError("The prediction model cannot process this match.") from exc
    if sport == "EPL":
        # The current EPL baseline predicts home win versus not-home-win.
        # Split the latter using only pre-match league results with smoothing.
        non_home_wins = sum(match.home_score <= match.away_score for match in history)
        draws = sum(match.home_score == match.away_score for match in history)
        draw_share = (draws + 1) / (non_home_wins + 2)
        draw_probability = (1 - home_probability) * draw_share
        away_probability = 1 - home_probability - draw_probability
    else:
        draw_probability = None
        away_probability = 1 - home_probability

    probabilities = {
        "home_win": home_probability,
        "away_win": away_probability,
    }
    if draw_probability is not None:
        probabilities["draw"] = draw_probability
    outcome = max(probabilities, key=probabilities.get)

    return {
        "predicted_outcome": outcome,
        "home_win_probability": home_probability,
        "away_win_probability": away_probability,
        "draw_probability": draw_probability,
        "confidence": probabilities[outcome],
        "model_version": metadata.get("artifact_version"),
    }
