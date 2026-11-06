"""Fail-closed prepared-feature inference using explicitly selected trusted local models."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
import pickle
import math
from typing import Callable, Mapping

import pandas as pd
from pydantic import ValidationError

from app.ml.features.feature_timestamps import validate_feature_cutoff
from app.ml.features.kickoff_safe_features import parse_aware_timestamp
from app.ml.features.historical_sport_features import SCHEMA_VERSION, feature_columns
from app.ml.historical_baselines import METHODS
from app.ml.training.historical_match_model import (
    HistoricalMatchModel, _guard as model_cutoff_guard, _matrix as validate_model_features,
    load_historical_model,
)
from app.schemas.prepared_predictions import PreparedPredictionRequest, PreparedPredictionResponse
from app.services.prediction_input_integrity import canonical_prediction_input_hash

UPCOMING_SOURCE_AGE_LIMIT = timedelta(hours=24)


class PredictionInterfaceError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = 422):
        super().__init__(message)
        self.code, self.message, self.status_code = code, message, status_code

    @property
    def detail(self):
        return {"code": self.code, "message": self.message}


@dataclass(frozen=True)
class TrustedModelSpec:
    path: Path
    model_version: str


class TrustedHistoricalModelRegistry:
    """Operator-selected allowlist only; no client paths or artifact discovery."""

    def __init__(self, specs: Mapping[str, TrustedModelSpec] | None = None, *, trusted_local: bool = False):
        self._specs = dict(specs or {})
        self._trusted_local = trusted_local is True
        self._cache: dict[str, HistoricalMatchModel] = {}
        for sport, spec in self._specs.items():
            feature_columns(sport)
            if sport != sport.upper() or not isinstance(spec, TrustedModelSpec) or not isinstance(spec.model_version, str) or not spec.model_version.strip():
                raise ValueError("Expected uppercase sports and explicit trusted model versions")

    def get(self, sport: str, requested_version: str) -> HistoricalMatchModel:
        spec = self._specs.get(sport)
        if spec is None or not self._trusted_local:
            raise PredictionInterfaceError("model_unavailable", "No trusted compatible model is configured for this sport.", 503)
        if requested_version != spec.model_version:
            raise PredictionInterfaceError("model_version_mismatch", "Requested model version is not the configured version.", 409)
        if sport not in self._cache:
            try:
                model = load_historical_model(spec.path, trusted_local=True)
                if model.metadata["sport"] != sport or model.metadata["model_version"] != spec.model_version:
                    raise ValueError("Configured artifact identity does not match allowlist")
            except (OSError, ValueError, TypeError, KeyError, AttributeError, EOFError, pickle.UnpicklingError) as exc:
                raise PredictionInterfaceError("model_unavailable", "The configured model is unavailable or incompatible.", 503) from exc
            self._cache[sport] = model
        return self._cache[sport]


class PreparedPredictionService:
    def __init__(self, registry: TrustedHistoricalModelRegistry, *, max_source_age: timedelta | None = None,
                 clock: Callable[[], datetime] | None = None):
        if max_source_age is not None and (not isinstance(max_source_age, timedelta) or max_source_age <= timedelta(0)):
            raise ValueError("max_source_age must be a positive timedelta or None")
        self.registry, self.max_source_age = registry, max_source_age
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def predict_prepared(self, request: PreparedPredictionRequest | Mapping) -> PreparedPredictionResponse:
        try:
            # Revalidate even model instances, which can otherwise be mutated or
            # constructed without validation by an in-process caller.
            payload = request.model_dump() if isinstance(request, PreparedPredictionRequest) else request
            request = PreparedPredictionRequest.model_validate(payload)
        except (ValidationError, TypeError, ValueError) as exc:
            raise PredictionInterfaceError("invalid_request", "Request fields or types are invalid.") from exc
        columns = feature_columns(request.sport)
        if request.feature_schema_version != SCHEMA_VERSION or request.feature_columns != columns:
            raise PredictionInterfaceError("feature_schema_mismatch", "Feature schema/version and ordered columns must match the model contract.", 409)
        if set(request.features) != set(columns):
            raise PredictionInterfaceError("invalid_features", "Provide exactly the declared predictor fields; metadata and labels are not predictors.")
        try:
            generated_at = parse_aware_timestamp(self.clock(), "prediction_time")
        except (ValueError, TypeError) as exc:
            raise PredictionInterfaceError("prediction_unavailable", "The prediction clock is unavailable.", 503) from exc
        if request.feature_as_of > generated_at:
            raise PredictionInterfaceError("future_feature_cutoff", "Feature availability cannot be later than prediction processing time.")
        try:
            values = {key: float("nan") if value is None else value for key, value in request.features.items()}
            frame = pd.DataFrame([{**values, "game_id": request.match_id, "sport": request.sport,
                                   "start_time": request.start_time, "feature_as_of": request.feature_as_of,
                                   "game_date": pd.Timestamp(request.start_time).tz_convert("UTC").normalize()}])
            validate_model_features(frame, request.sport)  # Counts/ranges/NaN policy, before loading/execution.
            validate_feature_cutoff(request.start_time, request.feature_as_of)
        except (ValueError, TypeError, OverflowError) as exc:
            raise PredictionInterfaceError("invalid_features_or_cutoff", "Features or the pre-kickoff prediction cutoff are invalid.") from exc
        for side in ("home", "away"):
            n, wins, losses = (request.features[f"{side}_season_{name}"] for name in ("matches", "wins", "losses"))
            tied_name = "ties" if request.sport == "NFL" else "draws" if request.sport == "EPL" else None
            tied = request.features[f"{side}_season_{tied_name}"] if tied_name else 0
            if (wins + losses + tied != n
                    or request.features[f"{side}_recent5_matches"] != min(5, n)
                    or request.features[f"{side}_recent10_matches"] != min(10, n)
                    or request.features[f"{side}_venue_matches"] > n):
                raise PredictionInterfaceError("invalid_feature_consistency", "Season, recent and venue counts are inconsistent.")
            for scope in ("season", "recent5", "recent10", "venue"):
                scored, conceded, margin = (values[f"{side}_{scope}_avg_{name}"] for name in ("scored", "conceded", "margin"))
                if all(math.isfinite(value) for value in (scored, conceded, margin)) and not math.isclose(
                    margin, scored - conceded, rel_tol=1e-9, abs_tol=1e-9,
                ):
                    raise PredictionInterfaceError("invalid_feature_consistency", "Scoring margin conflicts with scoring averages.")
        ids = [result.source_game_id.strip() for result in request.source_results]
        if any(not value for value in ids) or len(ids) != len(set(ids)) or request.match_id in ids:
            raise PredictionInterfaceError("invalid_provenance", "Source result identities must be nonblank and unique.")
        if len(ids) < max(request.features["home_season_matches"], request.features["away_season_matches"]):
            raise PredictionInterfaceError("missing_provenance", "Provide availability evidence for every historical result used by the features.")
        for result in request.source_results:
            if (result.result_available_at <= result.start_time
                    or pd.Timestamp(result.start_time).tz_convert("UTC").normalize() >= frame.iloc[0]["game_date"]
                    or result.result_available_at > request.feature_as_of):
                raise PredictionInterfaceError("historical_cutoff_violation", "Historical results must start on prior UTC days and be available by the prediction cutoff.")
        freshness = "not_evaluated"
        observed = request.source_observed_at
        if observed is not None:
            if observed > request.feature_as_of or any(result.result_available_at > observed for result in request.source_results):
                raise PredictionInterfaceError("invalid_source_timestamp", "Source observation must include historical results and precede the feature cutoff.")
        age_limit = self.max_source_age
        upcoming = request.start_time > generated_at
        age_reference = generated_at if upcoming else request.feature_as_of
        if upcoming:
            age_limit = min(age_limit, UPCOMING_SOURCE_AGE_LIMIT) if age_limit else UPCOMING_SOURCE_AGE_LIMIT
        if age_limit is not None:
            if observed is None:
                raise PredictionInterfaceError("freshness_unavailable", "The configured freshness policy requires a reliable source observation timestamp.")
            if age_reference - observed > age_limit:
                raise PredictionInterfaceError("stale_source", "Source data exceeds the configured age at the prediction cutoff.")
            freshness = "within_configured_age"
        model = self.registry.get(request.sport, request.model_version)
        try:
            model_cutoff_guard(model.metadata).predict(frame, METHODS[0], schema_version=request.feature_schema_version)
        except (ValueError, TypeError) as exc:
            raise PredictionInterfaceError("training_cutoff_violation", "The fitted model uses labels unavailable at this prediction cutoff.") from exc
        input_sha256 = canonical_prediction_input_hash(request)
        try:
            result = model.predict(frame, schema_version=request.feature_schema_version)[0]
            if result["model_version"] != request.model_version or result["match_id"] != request.match_id or result["sport"] != request.sport:
                raise ValueError("Prediction identity mismatch")
            return PreparedPredictionResponse(
                **result, generated_at=generated_at, prediction_cutoff=request.feature_as_of,
                freshness_status=freshness,
                source_freshness_limit_seconds=int(age_limit.total_seconds()) if age_limit else None,
                source_freshness_reference=("prediction_time" if upcoming else "feature_cutoff") if age_limit else None,
                input_sha256=input_sha256,
                probability_method="direct_multiclass" if request.sport == "EPL" else "direct_binary",
            )
        except (ValueError, TypeError, KeyError, IndexError, RuntimeError) as exc:
            raise PredictionInterfaceError("prediction_failed", "The configured model could not produce a valid prediction.", 502) from exc


@lru_cache(maxsize=1)
def get_prepared_prediction_service() -> PreparedPredictionService:
    """No implicit models or synthetic fallback. Backend must explicitly configure development artifacts."""
    return PreparedPredictionService(TrustedHistoricalModelRegistry())
