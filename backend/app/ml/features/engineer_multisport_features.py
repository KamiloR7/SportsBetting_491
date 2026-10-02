"""Prior-day features and date-grouped chronological holdout."""
from __future__ import annotations

import pandas as pd

from app.ml.features.prepare_multisport_data import validate_games

FEATURE_COLUMNS = [
    "home_win_rate", "away_win_rate", "home_avg_score", "away_avg_score",
    "home_avg_allowed", "away_avg_allowed",
]


def create_features(games: pd.DataFrame) -> pd.DataFrame:
    ordered = validate_games("NFL", games)
    ordered["game_date"] = ordered["game_date"].dt.normalize()
    history = {}
    rows = []
    for _, day_games in ordered.groupby("game_date", sort=True):
        for game in day_games.to_dict("records"):
            row = {key: game[key] for key in ("game_id", "game_date", "home_team", "away_team")}
            for side in ("home", "away"):
                count, wins, scored, allowed = history.get(game[f"{side}_team"], (0, 0, 0, 0))
                row[f"{side}_win_rate"] = wins / count if count else 0.0
                row[f"{side}_avg_score"] = scored / count if count else 0.0
                row[f"{side}_avg_allowed"] = allowed / count if count else 0.0
            row["outcome"] = int(game["home_score"] > game["away_score"])
            rows.append(row)
        for game in day_games.to_dict("records"):
            for side, opponent in (("home", "away"), ("away", "home")):
                team = game[f"{side}_team"]
                count, wins, scored, allowed = history.get(team, (0, 0, 0, 0))
                score, conceded = game[f"{side}_score"], game[f"{opponent}_score"]
                history[team] = (count + 1, wins + int(score > conceded), scored + score, allowed + conceded)
    return pd.DataFrame(rows)


def chronological_split(data: pd.DataFrame, test_fraction: float = 0.2) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction must be between 0 and 1")
    if len(data) < 2:
        raise ValueError("At least two rows are required")
    ordered = data.copy()
    ordered["game_date"] = pd.to_datetime(ordered["game_date"], format="ISO8601", utc=True, errors="raise").dt.normalize()
    if ordered["game_date"].isna().any():
        raise ValueError("Missing game_date")
    ordered = ordered.sort_values(["game_date", "game_id"]).reset_index(drop=True)
    boundaries = [index for index in range(1, len(ordered))
                  if ordered.loc[index, "game_date"] != ordered.loc[index - 1, "game_date"]]
    if not boundaries:
        raise ValueError("At least two distinct game dates are required")
    target = len(ordered) * (1 - test_fraction)
    boundary = min(boundaries, key=lambda index: abs(index - target))
    return ordered.iloc[:boundary].copy(), ordered.iloc[boundary:].copy()
