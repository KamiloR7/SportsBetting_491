"""Sport-specific match outcome labels."""


def label_match_outcome(sport, home_score, away_score, status):
    """
    Return the outcome label for a completed match.

    NBA/NFL: home_win or away_win
    UEFA: home_win, draw, or away_win

    Nonfinal matches return None.
    """

    sport = sport.upper()
    status = status.upper()

    if sport not in {"NBA", "NFL", "UEFA"}:
        raise ValueError(f"Unsupported sport: {sport}")

    # Exclude unfinished matches from training.
    if status != "FINAL":
        return None

    if (
        isinstance(home_score, bool)
        or isinstance(away_score, bool)
        or not isinstance(home_score, int)
        or not isinstance(away_score, int)
        or home_score < 0
        or away_score < 0
    ):
        raise ValueError("Final scores must be nonnegative integers")

    if home_score > away_score:
        return "home_win"

    if home_score < away_score:
        return "away_win"

    # UEFA soccer supports draws.
    if sport == "UEFA":
        return "draw"

    # A tied NBA/NFL score does not fit the binary winner model.
    # Exclude it instead of incorrectly labeling a winner.
    return None