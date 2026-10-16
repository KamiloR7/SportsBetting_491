"""Sprint 3 - S3-01.04: Feature timestamp safeguard tests."""

from datetime import datetime, timezone, timedelta

import pytest

from app.ml.features.feature_timestamps import validate_feature_cutoff


# =====================================
# Valid timestamps
# =====================================

def test_features_before_kickoff_are_allowed():
    kickoff = datetime(2026, 10, 15, 19, 0, tzinfo=timezone.utc)
    feature_time = datetime(2026, 10, 15, 17, 0, tzinfo=timezone.utc)

    assert validate_feature_cutoff(kickoff, feature_time)


# =====================================
# Reject features at or after kickoff
# =====================================

@pytest.mark.parametrize("hour", [19, 20, 21])
def test_features_at_or_after_kickoff_are_rejected(hour):
    kickoff = datetime(2026, 10, 15, 19, 0, tzinfo=timezone.utc)
    feature_time = datetime(2026, 10, 15, hour, 0, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="before match kickoff"):
        validate_feature_cutoff(kickoff, feature_time)


# =====================================
# Reject timestamps without timezone
# =====================================

def test_rejects_timezone_naive_timestamp():
    kickoff = datetime(2026, 10, 15, 19, 0, tzinfo=timezone.utc)
    feature_time = datetime(2026, 10, 15, 17, 0)

    with pytest.raises(ValueError, match="timezone-aware"):
        validate_feature_cutoff(kickoff, feature_time)


# =====================================
# Reject missing timestamps
# =====================================

def test_rejects_missing_kickoff():
    feature_time = datetime(2026, 10, 15, 17, 0, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="timezone-aware"):
        validate_feature_cutoff(None, feature_time)


# =====================================
# Reject future historical results
# =====================================

def test_rejects_future_result_leakage():
    kickoff = datetime(2026, 10, 15, 19, 0, tzinfo=timezone.utc)
    feature_time = datetime(2026, 10, 15, 17, 0, tzinfo=timezone.utc)

    future_result = datetime(2026, 10, 15, 18, 0, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="unavailable at prediction time"):
        validate_feature_cutoff(
            kickoff,
            feature_time,
            source_result_times=[future_result],
        )


# =====================================
# Allow valid historical results
# =====================================

def test_allows_past_historical_results():
    kickoff = datetime(2026, 10, 15, 19, 0, tzinfo=timezone.utc)
    feature_time = datetime(2026, 10, 15, 17, 0, tzinfo=timezone.utc)

    past_result = datetime(2026, 10, 14, 22, 0, tzinfo=timezone.utc)

    assert validate_feature_cutoff(
        kickoff,
        feature_time,
        source_result_times=[past_result],
    )


# =====================================
# Compare different timezones correctly
# =====================================

def test_different_timezones_are_compared_correctly():
    kickoff = datetime(2026, 10, 15, 19, 0, tzinfo=timezone.utc)

    pacific = timezone(timedelta(hours=-7))
    feature_time = datetime(2026, 10, 15, 11, 0, tzinfo=pacific)

    assert validate_feature_cutoff(kickoff, feature_time)