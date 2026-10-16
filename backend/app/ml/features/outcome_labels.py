"""Sport-specific match outcome labels for NFL, MLB, and EPL."""


def label_match_outcome(sport, home_score, away_score, status):
    """
    Return the outcome label for a completed match.

    NFL/MLB: home_win or away_win
    EPL: home_win, draw, or away_win

    Nonfinal matches return None.
    Tied NFL/MLB games are excluded from binary winner training.
    """

    sport = sport.upper()
    status = status.upper()

    if sport not in {"NFL", "MLB", "EPL"}:
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

    # EPL supports draws as a separate prediction outcome.
    if sport == "EPL":
        return "draw"

    # Tied NFL/MLB games do not have a binary winner.
    return None