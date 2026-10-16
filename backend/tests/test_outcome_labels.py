"""Tests for NFL, MLB, and EPL match outcome labeling."""

import pytest

from app.ml.features.outcome_labels import label_match_outcome


@pytest.mark.parametrize(
    "sport,home_score,away_score,expected",
    [
        # NFL: binary outcomes
        ("NFL", 28, 21, "home_win"),
        ("NFL", 17, 24, "away_win"),

        # MLB: binary outcomes
        ("MLB", 5, 3, "home_win"),
        ("MLB", 2, 6, "away_win"),

        # EPL: three-way outcomes
        ("EPL", 2, 0, "home_win"),
        ("EPL", 1, 1, "draw"),
        ("EPL", 0, 3, "away_win"),
    ],
)
def test_completed_match_outcomes(
    sport, home_score, away_score, expected
):
    result = label_match_outcome(
        sport, home_score, away_score, "FINAL"
    )

    assert result == expected


@pytest.mark.parametrize(
    "status",
    ["SCHEDULED", "LIVE", "POSTPONED", "CANCELLED"],
)
def test_nonfinal_matches_are_excluded(status):
    result = label_match_outcome(
        "NFL", 0, 0, status
    )

    assert result is None


@pytest.mark.parametrize("sport", ["NFL", "MLB"])
def test_binary_sports_exclude_ties(sport):
    result = label_match_outcome(
        sport, 21, 21, "FINAL"
    )

    assert result is None


def test_epl_draw_is_not_an_away_win():
    result = label_match_outcome(
        "EPL", 2, 2, "FINAL"
    )

    assert result == "draw"


def test_rejects_negative_scores():
    with pytest.raises(ValueError, match="nonnegative integers"):
        label_match_outcome(
            "MLB", -5, 3, "FINAL"
        )


@pytest.mark.parametrize(
    "home_score,away_score",
    [
        (True, 1),
        (1, False),
        (1.5, 2),
        (2, "3"),
    ],
)
def test_rejects_invalid_score_types(home_score, away_score):
    with pytest.raises(ValueError, match="nonnegative integers"):
        label_match_outcome(
            "NFL", home_score, away_score, "FINAL"
        )


@pytest.mark.parametrize("sport", ["NBA", "UEFA", "NHL"])
def test_rejects_unsupported_sport(sport):
    with pytest.raises(ValueError, match="Unsupported sport"):
        label_match_outcome(
            sport, 5, 3, "FINAL"
        )


def test_label_conversion_is_deterministic():
    results = [
        label_match_outcome(
            "EPL", 1, 1, "FINAL"
        )
        for _ in range(10)
    ]

    assert results == ["draw"] * 10