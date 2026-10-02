from data.validation import validate_match


def valid_match():
    return {
        "match_id": "NFL-001",
        "sport": "NFL",
        "home_team_id": "KC",
        "away_team_id": "BUF",
        "status": "scheduled",
    }


def test_valid_match():
    assert validate_match(valid_match()) is True


def test_missing_match_id():
    match = valid_match()
    match["match_id"] = None

    assert validate_match(match) is False


def test_same_home_and_away_team():
    match = valid_match()
    match["away_team_id"] = "KC"

    assert validate_match(match) is False


def test_invalid_status():
    match = valid_match()
    match["status"] = "unknown"

    assert validate_match(match) is False


def test_postponed_match():
    match = valid_match()
    match["status"] = "postponed"

    assert validate_match(match) is True


def test_cancelled_match():
    match = valid_match()
    match["status"] = "cancelled"

    assert validate_match(match) is True

def test_missing_home_team():
    match = valid_match()
    match["home_team_id"] = None

    assert validate_match(match) is False


def test_missing_away_team():
    match = valid_match()
    match["away_team_id"] = None

    assert validate_match(match) is False


def test_completed_match_status():
    match = valid_match()
    match["status"] = "completed"

    assert validate_match(match) is True


def test_in_progress_match_status():
    match = valid_match()
    match["status"] = "in_progress"

    assert validate_match(match) is True