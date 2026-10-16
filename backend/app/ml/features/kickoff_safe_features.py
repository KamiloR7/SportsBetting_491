"""Kickoff-aware safeguards for existing historical ML features."""

from datetime import datetime

from app.ml.features.engineer_multisport_features import create_features
from app.ml.features.feature_timestamps import validate_feature_cutoff
from app.ml.features.prepare_multisport_data import validate_games


TIME_COLUMNS = {
    "start_time",
    "feature_as_of",
    "result_available_at",
}


def parse_aware_timestamp(value, field_name):
    """Accept timezone-aware datetimes or ISO 8601 strings."""

    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise ValueError(
                f"Invalid {field_name}"
            ) from exc

    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(
            f"{field_name} must be timezone-aware"
        )

    return value


def create_kickoff_safe_features(games):
    """Generate historical features after verifying result availability."""

    missing = TIME_COLUMNS - set(games.columns)

    if missing:
        raise ValueError(
            f"Missing timestamp columns: {sorted(missing)}"
        )

    # Reuse the existing validated NFL baseline input contract.
    ordered = validate_games("NFL", games)

    for column in TIME_COLUMNS:
        ordered[column] = ordered[column].map(
            lambda value: parse_aware_timestamp(value, column)
        )

    # A completed result cannot be available before the match starts.
    for _, game in ordered.iterrows():
        if game["result_available_at"] < game["start_time"]:
            raise ValueError(
                "Result availability predates match kickoff"
            )

    for _, game in ordered.iterrows():
        game_day = game["game_date"].normalize()

        teams = [game["home_team"], game["away_team"]]

        # Mirror the original generator's prior-day team history.
        historical = ordered[
            (ordered["game_date"].dt.normalize() < game_day)
            & (
                ordered["home_team"].isin(teams)
                | ordered["away_team"].isin(teams)
            )
        ]

        validate_feature_cutoff(
            start_time=game["start_time"],
            feature_as_of=game["feature_as_of"],
            source_result_times=historical[
                "result_available_at"
            ].tolist(),
        )

    return create_features(ordered)