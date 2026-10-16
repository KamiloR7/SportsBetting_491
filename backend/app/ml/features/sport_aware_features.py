"""Sport-aware training features for NFL, MLB, and EPL."""

import pandas as pd

from app.ml.features.engineer_multisport_features import create_features
from app.ml.features.prepare_multisport_data import validate_games


SUPPORTED_SPORTS = {"NFL", "MLB", "EPL"}


def create_sport_aware_features(
    games: pd.DataFrame,
    sport: str,
) -> pd.DataFrame:
    """Generate prior-day features with sport-specific outcome labels."""

    sport = sport.upper()

    if sport not in SUPPORTED_SPORTS:
        raise ValueError(f"Unsupported sport: {sport}")

    # Validate the original match data.
    validated = validate_games(sport, games)

    # Reuse existing historical features.
    # These are computed before relabeling or removing ties.
    features = create_features(validated)

    # Build labels from final match scores.
    labels = {}

    for game in validated.to_dict("records"):
        home_score = game["home_score"]
        away_score = game["away_score"]

        if home_score > away_score:
            outcome = "home_win"
        elif away_score > home_score:
            outcome = "away_win"
        elif sport == "EPL":
            outcome = "draw"
        else:
            # NFL ties have no binary winner.
            # MLB ties, if present in an input, are excluded too.
            outcome = None

        labels[game["game_id"]] = outcome

    features["outcome"] = features["game_id"].map(labels)

    # Exclude games without a valid training label.
    features = features.dropna(subset=["outcome"])

    if features.empty:
        raise ValueError(f"No labeled {sport} games available")

    return features.reset_index(drop=True)