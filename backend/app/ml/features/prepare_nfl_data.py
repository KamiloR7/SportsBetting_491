import pandas as pd
from pathlib import Path


RAW_DATA_PATH = Path("data/raw/nfl_games.csv")
PROCESSED_DATA_PATH = Path("data/processed/nfl_model_data.csv")


def load_nfl_games():
    """Load completed NFL regular-season games."""

    games = pd.read_csv(RAW_DATA_PATH)

    # Keep regular-season games only.
    games = games[games["game_type"] == "REG"].copy()

    # Remove games without final scores.
    games = games.dropna(subset=["home_score", "away_score"])

    # Convert dates and sort games chronologically.
    games["gameday"] = pd.to_datetime(games["gameday"])
    games = games.sort_values("gameday").reset_index(drop=True)

    return games


def calculate_team_stats(previous_games, team, location):
    """Calculate team statistics using only previous games."""

    team_games = previous_games[
        (previous_games["home_team"] == team)
        | (previous_games["away_team"] == team)
    ]

    if team_games.empty:
        return None

    wins = 0
    scores = []
    scores_allowed = []
    recent_results = []

    for _, game in team_games.iterrows():

        is_home = game["home_team"] == team

        if is_home:
            team_score = game["home_score"]
            opponent_score = game["away_score"]
        else:
            team_score = game["away_score"]
            opponent_score = game["home_score"]

        won = team_score > opponent_score

        wins += int(won)
        scores.append(team_score)
        scores_allowed.append(opponent_score)
        recent_results.append(int(won))

    # Calculate home or away performance.
    if location == "home":
        location_games = team_games[
            team_games["home_team"] == team
        ]
    else:
        location_games = team_games[
            team_games["away_team"] == team
        ]

    location_wins = 0

    for _, game in location_games.iterrows():

        if location == "home":
            won = game["home_score"] > game["away_score"]
        else:
            won = game["away_score"] > game["home_score"]

        location_wins += int(won)

    if len(location_games) > 0:
        location_win_pct = location_wins / len(location_games)
    else:
        location_win_pct = 0.0

    recent_five = recent_results[-5:]

    return {
        "win_pct": wins / len(team_games),
        "recent_form": sum(recent_five) / len(recent_five),
        "avg_scored": sum(scores) / len(scores),
        "avg_allowed": sum(scores_allowed) / len(scores_allowed),
        "location_win_pct": location_win_pct,
    }


def create_model_dataset(games):
    """Create model-ready rows from historical NFL games."""

    model_rows = []

    # Process each NFL season independently.
    for season in sorted(games["season"].unique()):

        season_games = games[
            games["season"] == season
        ].sort_values("gameday").reset_index(drop=True)

        for index, game in season_games.iterrows():

            # Only games before the current game may be used.
            previous_games = season_games.iloc[:index]

            home_stats = calculate_team_stats(
                previous_games,
                game["home_team"],
                "home",
            )

            away_stats = calculate_team_stats(
                previous_games,
                game["away_team"],
                "away",
            )

            # Skip games where either team has no previous
            # games in the current season.
            if home_stats is None or away_stats is None:
                continue

            # NFL ties are uncommon and do not fit our
            # binary home-win/away-win baseline.
            if game["home_score"] == game["away_score"]:
                continue

            outcome = int(
                game["home_score"] > game["away_score"]
            )

            model_rows.append(
                {
                    "season": game["season"],
                    "week": game["week"],
                    "gameday": game["gameday"],
                    "home_team": game["home_team"],
                    "away_team": game["away_team"],

                    "home_win_pct": home_stats["win_pct"],
                    "away_win_pct": away_stats["win_pct"],

                    "home_recent_form": home_stats["recent_form"],
                    "away_recent_form": away_stats["recent_form"],

                    "home_avg_scored": home_stats["avg_scored"],
                    "away_avg_scored": away_stats["avg_scored"],

                    "home_avg_allowed": home_stats["avg_allowed"],
                    "away_avg_allowed": away_stats["avg_allowed"],

                    "home_home_win_pct":
                        home_stats["location_win_pct"],

                    "away_away_win_pct":
                        away_stats["location_win_pct"],

                    # 1 = home team won
                    # 0 = away team won
                    "outcome": outcome,
                }
            )

    return pd.DataFrame(model_rows)


def main():

    games = load_nfl_games()

    print(f"Regular-season games loaded: {len(games)}")
    print(
        f"Seasons: {games['season'].min()} - "
        f"{games['season'].max()}"
    )

    print("\nCreating model dataset...")

    model_data = create_model_dataset(games)

    PROCESSED_DATA_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    model_data.to_csv(
        PROCESSED_DATA_PATH,
        index=False,
    )

    print(f"Model-ready games created: {len(model_data)}")
    print(
        f"Dataset saved to: {PROCESSED_DATA_PATH}"
    )

    print("\nModel features:")
    print(model_data.head())


if __name__ == "__main__":
    main()