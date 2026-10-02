"""Create leakage-safe features and chronological train/test splits."""
from __future__ import annotations

import pandas as pd

FEATURE_COLUMNS = ["home_win_rate", "away_win_rate", "home_avg_score", "away_avg_score", "home_avg_allowed", "away_avg_allowed"]


def _history(games: pd.DataFrame, team: str, date: pd.Timestamp) -> pd.DataFrame:
    prior = games[games["game_date"] < date]
    home = prior[prior["home_team"] == team].assign(team_score=lambda x: x["home_score"], opponent_score=lambda x: x["away_score"])
    away = prior[prior["away_team"] == team].assign(team_score=lambda x: x["away_score"], opponent_score=lambda x: x["home_score"])
    return pd.concat([home, away], ignore_index=True)


def _stats(games: pd.DataFrame, team: str, date: pd.Timestamp) -> dict[str, float]:
    history = _history(games, team, date)
    if history.empty:
        return {"win_rate": 0.0, "avg_score": 0.0, "avg_allowed": 0.0}
    return {"win_rate": float((history["team_score"] > history["opponent_score"]).mean()), "avg_score": float(history["team_score"].mean()), "avg_allowed": float(history["opponent_score"].mean())}


def create_features(games: pd.DataFrame) -> pd.DataFrame:
    """Create pre-game features using only matches before each match."""
    required = {"game_id", "game_date", "home_team", "away_team", "home_score", "away_score"}
    missing = required - set(games.columns)
    if missing:
        raise ValueError(f"Missing feature input columns: {', '.join(sorted(missing))}")
    ordered = games.copy()
    ordered["game_date"] = pd.to_datetime(ordered["game_date"], utc=True)
    ordered = ordered.sort_values(["game_date", "game_id"]).reset_index(drop=True)
    rows = []
    for _, game in ordered.iterrows():
        home, away = _stats(ordered, game["home_team"], game["game_date"]), _stats(ordered, game["away_team"], game["game_date"])
        rows.append({"game_id": game["game_id"], "game_date": game["game_date"], "home_team": game["home_team"], "away_team": game["away_team"], "home_win_rate": home["win_rate"], "away_win_rate": away["win_rate"], "home_avg_score": home["avg_score"], "away_avg_score": away["avg_score"], "home_avg_allowed": home["avg_allowed"], "away_avg_allowed": away["avg_allowed"], "outcome": int(game["home_score"] > game["away_score"])})
    return pd.DataFrame(rows)


def chronological_split(data: pd.DataFrame, test_fraction: float = 0.2) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split older matches for training and newer matches for testing."""
    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction must be between 0 and 1")
    ordered = data.sort_values(["game_date", "game_id"]).reset_index(drop=True)
    index = min(max(1, int(len(ordered) * (1 - test_fraction))), len(ordered) - 1)
    return ordered.iloc[:index].copy(), ordered.iloc[index:].copy()
