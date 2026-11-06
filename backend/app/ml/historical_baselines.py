"""Reproducible frequency and form baselines for validated historical features."""
from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Real

import pandas as pd

from app.ml.features.feature_timestamps import validate_feature_cutoff
from app.ml.features.historical_sport_features import (
    SCHEMA_VERSION, SportFeatureDataset, feature_columns,
)
from app.ml.features.kickoff_safe_features import parse_aware_timestamp
from app.ml.probability_validation import validate_sport_probabilities

BASELINE_VERSION = "historical_baselines_v1"
METHODS = ("historical_home_frequency", "team_form")


class InsufficientHistoryError(ValueError):
    """A valid input has insufficient observed history; do not invent features."""


def outcome_classes(sport: str) -> tuple[str, ...]:
    feature_columns(sport)  # Reuse supported-sport validation.
    return ("home_win", "draw", "away_win") if sport.upper() == "EPL" else ("home_win", "away_win")


def _positive_integer(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")


def _number(value, name, *, count=False, nonnegative=False):
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite numeric data")
    value = float(value)
    if (count or nonnegative) and value < 0:
        raise ValueError(f"{name} must be nonnegative")
    if count and not value.is_integer():
        raise ValueError(f"{name} must be an integer count")
    return value


def _validate_rows(frame, sport, *, fitting=False):
    required = {"game_id", "sport", "game_date", "start_time", "feature_as_of"}
    if fitting:
        required |= {"outcome", "result_available_at"}
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        raise ValueError("Input must be a nonempty feature DataFrame")
    if not frame.columns.is_unique:
        raise ValueError("Duplicate feature columns")
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing baseline input columns: {sorted(missing)}")
    if not frame["sport"].eq(sport).all():
        raise ValueError("Input sport does not match fitted baseline")
    ids = frame["game_id"]
    if not ids.map(lambda value: isinstance(value, str) and bool(value.strip())).all() or ids.duplicated().any():
        raise ValueError("Match identifiers must be nonblank unique strings")
    normalized = []
    for row in frame.to_dict("records"):
        start = pd.Timestamp(parse_aware_timestamp(row["start_time"], "start_time")).tz_convert("UTC")
        cutoff = pd.Timestamp(parse_aware_timestamp(row["feature_as_of"], "feature_as_of")).tz_convert("UTC")
        validate_feature_cutoff(start, cutoff)
        day = pd.Timestamp(parse_aware_timestamp(row["game_date"], "game_date")).tz_convert("UTC").normalize()
        if day != start.normalize():
            raise ValueError("Match date conflicts with UTC kickoff day")
        normalized.append((day, cutoff))
        if fitting:
            available = parse_aware_timestamp(row["result_available_at"], "result_available_at")
            if available <= start:
                raise ValueError("Training result availability must follow kickoff")
    return normalized


@dataclass(frozen=True)
class BaselinePredictor:
    """Training-only home-side frequencies and immutable evaluation cutoffs."""

    sport: str
    class_counts: tuple[int, ...]
    training_end_day: pd.Timestamp
    labels_available_at: pd.Timestamp
    excluded_training_ties: int
    min_team_matches: int = 1
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def fit(cls, dataset: SportFeatureDataset, *, min_training_matches=1, min_team_matches=1):
        """Estimate frequencies from train only; no held-out label access."""
        _positive_integer(min_training_matches, "min_training_matches")
        _positive_integer(min_team_matches, "min_team_matches")
        expected = feature_columns(dataset.sport)
        if dataset.schema_version != SCHEMA_VERSION or dataset.feature_columns != expected:
            raise ValueError("Incompatible feature schema/version or ordering")
        train = dataset.train
        sport = dataset.sport.upper()
        times = _validate_rows(train, sport, fitting=True)
        if set(expected) - set(train.columns):
            raise ValueError("Training frame does not contain the declared feature schema")
        classes = outcome_classes(sport)
        labels = train["outcome"]
        ties = labels.isna()
        if (sport != "NFL" and ties.any()) or not labels[~ties].isin(classes).all():
            raise ValueError(f"Invalid training outcome labels for {sport}")
        if (~ties).sum() < min_training_matches:
            raise InsufficientHistoryError("Insufficient labeled training history")
        availability = [pd.Timestamp(parse_aware_timestamp(value, "result_available_at")).tz_convert("UTC")
                        for value in train["result_available_at"]]
        return cls(
            sport=sport, class_counts=tuple(int(labels.eq(label).sum()) for label in classes),
            training_end_day=max(day for day, _ in times),
            labels_available_at=max(availability), excluded_training_ties=int(ties.sum()),
            min_team_matches=min_team_matches,
        )

    @property
    def probabilities(self) -> dict[str, float]:
        total = sum(self.class_counts)
        return {label: count / total for label, count in zip(outcome_classes(self.sport), self.class_counts)}

    def predict(self, features: pd.DataFrame, method: str, *, schema_version: str) -> list[dict]:
        """Predict only matches after the fitted partition with available labels.

        Feature provenance must come from the validated pipeline; timestamps alone
        cannot prove that arbitrary externally supplied statistics are historical.
        """
        if method not in METHODS:
            raise ValueError(f"Unsupported baseline method: {method}")
        if schema_version != self.schema_version:
            raise ValueError("Incompatible feature schema version")
        times = _validate_rows(features, self.sport)
        for day, cutoff in times:
            if day <= self.training_end_day:
                raise ValueError("Prediction must follow all training UTC days")
            if cutoff < self.labels_available_at:
                raise ValueError("Training labels unavailable at prediction cutoff")
        results = []
        for row in features.to_dict("records"):
            probabilities = self.probabilities if method == METHODS[0] else self._form_probabilities(row)
            validate_sport_probabilities(self.sport, probabilities)
            results.append({
                "match_id": row["game_id"], "sport": self.sport,
                "predicted_outcome": max(probabilities, key=probabilities.get),
                "probabilities": probabilities, "baseline_method": method,
                "feature_schema_version": self.schema_version,
                "baseline_version": BASELINE_VERSION,
            })
        return results

    def _form_probabilities(self, row):
        forms, scoring = {}, {}
        for side in ("home", "away"):
            fields = ["season_matches", "season_wins", "season_losses", "recent5_matches",
                      "recent5_avg_scored", "recent5_avg_conceded", "recent5_avg_margin"]
            tied_field = "season_ties" if self.sport == "NFL" else "season_draws" if self.sport == "EPL" else None
            if tied_field:
                fields.append(tied_field)
            missing = {f"{side}_{field}" for field in fields} - set(row)
            if missing:
                raise ValueError(f"Missing team-form features: {sorted(missing)}")
            counts = {field: _number(row[f"{side}_{field}"], f"{side}_{field}", count=True)
                      for field in fields if field.startswith("season_") or field == "recent5_matches"}
            n, wins, losses = (counts[f"season_{name}"] for name in ("matches", "wins", "losses"))
            tied = counts[tied_field] if tied_field else 0
            recent = counts["recent5_matches"]
            if wins + losses + tied != n or recent != min(5, n):
                raise ValueError("Inconsistent season or recent-match counts")
            if n < self.min_team_matches or recent < min(5, self.min_team_matches):
                raise InsufficientHistoryError(f"Insufficient {side}-team history for team_form")
            scored = _number(row[f"{side}_recent5_avg_scored"], "recent5_avg_scored", nonnegative=True)
            conceded = _number(row[f"{side}_recent5_avg_conceded"], "recent5_avg_conceded", nonnegative=True)
            margin = _number(row[f"{side}_recent5_avg_margin"], "recent5_avg_margin")
            if not math.isclose(margin, scored - conceded, rel_tol=1e-9, abs_tol=1e-9):
                raise ValueError("Scoring margin conflicts with scored/conceded averages")
            forms[side] = (wins + 0.5 * tied) / n
            scoring[side] = (scored, conceded, margin)
        scale = max(1.0, sum(values[0] + values[1] for values in scoring.values()))
        contrast = (scoring["home"][2] - scoring["away"][2]) / scale
        signal = ((forms["home"] - forms["away"]) + contrast) / 2
        decisive_home = (1 + signal) / 2
        if self.sport == "EPL":
            draw = self.probabilities["draw"] * (1 - abs(signal))
            return {"home_win": (1 - draw) * decisive_home, "draw": draw,
                    "away_win": (1 - draw) * (1 - decisive_home)}
        return {"home_win": decisive_home, "away_win": 1 - decisive_home}
