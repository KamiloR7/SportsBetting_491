import pytest

from app.ml.features.outcome_labels import label_match_outcome


# =====================================
# Sprint 3 - S3-04.01
# Test sport-specific outcome labels
# =====================================

@pytest.mark.parametrize(
    "sport, home_score, away_score, expected",
    [
        # NBA - binary outcomes
        ("NBA", 115, 108, "home_win"),
        ("NBA", 98, 112, "away_win"),

        # NFL - binary outcomes
        ("NFL", 28, 21, "home_win"),
        ("NFL", 17, 24, "away_win"),

        # UEFA - three-way outcomes
        ("UEFA", 2, 0, "home_win"),
        ("UEFA", 1, 1, "draw"),
        ("UEFA", 0, 3, "away_win"),
    ],
)
def test_completed_match_outcomes(
    sport, home_score, away_score, expected
):
    result = label_match_outcome(
        sport,
        home_score,
        away_score,
        "FINAL",
    )

    assert result == expected


# =====================================
# Exclude unfinished matches
# =====================================

@pytest.mark.parametrize(
    "status",
    [
        "SCHEDULED",
        "LIVE",
        "POSTPONED",
        "CANCELLED",
    ],
)
def test_nonfinal_matches_are_excluded(status):
    result = label_match_outcome(
        "NBA",
        0,
        0,
        status,
    )

    assert result is None


# =====================================
# Exclude tied NBA/NFL games
# =====================================

@pytest.mark.parametrize("sport", ["NBA", "NFL"])
def test_binary_sports_exclude_ties(sport):
    result = label_match_outcome(
        sport,
        21,
        21,
        "FINAL",
    )

    assert result is None


# =====================================
# Reject invalid scores
# =====================================

def test_rejects_negative_scores():
    with pytest.raises(ValueError):
        label_match_outcome(
            "NBA",
            -5,
            100,
            "FINAL",
        )


# =====================================
# Reject unsupported sports
# =====================================

def test_rejects_unsupported_sport():
    with pytest.raises(ValueError):
        label_match_outcome(
            "MLB",
            5,
            3,
            "FINAL",
        )