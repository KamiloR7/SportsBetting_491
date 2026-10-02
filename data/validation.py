VALID_STATUSES = {
    "scheduled",
    "in_progress",
    "completed",
    "postponed",
    "cancelled",
}


def validate_match(match):
    """Validate required fields in a normalized match record."""

    required_fields = [
        "match_id",
        "sport",
        "home_team_id",
        "away_team_id",
        "status",
    ]

    for field in required_fields:
        if match.get(field) is None:
            return False

    if match["home_team_id"] == match["away_team_id"]:
        return False

    if match["status"] not in VALID_STATUSES:
        return False

    return True