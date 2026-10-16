"""Sprint 3 - Validate ML feature timestamps to prevent data leakage."""

from datetime import datetime


def _require_timezone_aware(value, field_name):
    """Reject missing, invalid, or timezone-naive timestamps."""

    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(
            f"{field_name} must be a timezone-aware datetime"
        )


def validate_feature_cutoff(
    start_time,
    feature_as_of,
    source_result_times=None,
):
    """
    Verify that predictive features use only pre-kickoff information.

    start_time: Match kickoff timestamp.
    feature_as_of: Timestamp at which features were available.
    source_result_times: Availability timestamps of historical results
                         used to construct the features.
    """

    _require_timezone_aware(start_time, "start_time")
    _require_timezone_aware(feature_as_of, "feature_as_of")

    # Features must be available before kickoff.
    if feature_as_of >= start_time:
        raise ValueError(
            "Feature timestamp must be before match kickoff"
        )

    # Historical results cannot come from the future.
    if source_result_times is not None:
        for result_time in source_result_times:
            _require_timezone_aware(
                result_time,
                "source_result_time",
            )

            if result_time > feature_as_of:
                raise ValueError(
                    "Feature uses a result unavailable at prediction time"
                )

    return True