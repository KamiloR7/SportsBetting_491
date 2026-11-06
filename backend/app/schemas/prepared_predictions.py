"""Prepared-feature request/response contracts, separate from legacy match-ID APIs."""
from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictFloat, StrictInt, StrictStr, field_validator, model_validator

from app.ml.features.historical_sport_features import SCHEMA_VERSION
from app.ml.historical_baselines import outcome_classes
from app.ml.probability_validation import validate_sport_probabilities
from app.ml.training.historical_match_model import MODEL_FAMILY


class _StrictTimestampModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("start_time", "feature_as_of", "result_available_at", "source_observed_at", mode="before", check_fields=False)
    @classmethod
    def timestamp_type(cls, value):
        if value is not None and not isinstance(value, (str, datetime)):
            raise ValueError("Timestamps must be aware datetimes or ISO 8601 strings")
        return value


class HistoricalResultAvailability(_StrictTimestampModel):
    source_game_id: StrictStr = Field(min_length=1)
    start_time: AwareDatetime
    result_available_at: AwareDatetime


class PreparedPredictionRequest(_StrictTimestampModel):
    match_id: StrictStr = Field(min_length=1)
    sport: Literal["NFL", "MLB", "EPL"]
    start_time: AwareDatetime
    feature_as_of: AwareDatetime
    feature_schema_version: StrictStr
    feature_columns: list[StrictStr]
    features: dict[StrictStr, StrictFloat | StrictInt | None]
    model_version: StrictStr = Field(min_length=1)
    source_results: list[HistoricalResultAvailability]
    source_observed_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def nonblank_identifiers(self):
        if not self.match_id.strip() or not self.model_version.strip():
            raise ValueError("Match ID and model version must not be blank")
        return self


class PreparedPredictionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_id: str
    sport: Literal["NFL", "MLB", "EPL"]
    predicted_outcome: Literal["home_win", "draw", "away_win"]
    probabilities: dict[StrictStr, StrictFloat | StrictInt]
    class_order: list[str]
    model_identifier: str
    model_version: str
    feature_schema_version: str
    generated_at: AwareDatetime
    prediction_cutoff: AwareDatetime
    prediction_method: Literal["historical_logistic_regression"] = "historical_logistic_regression"
    source: Literal["trusted_local_development_artifact"] = "trusted_local_development_artifact"
    freshness_status: Literal["not_evaluated", "within_configured_age"]
    source_freshness_limit_seconds: StrictInt | None = None
    source_freshness_reference: Literal["prediction_time", "feature_cutoff"] | None = None
    input_sha256: StrictStr = Field(pattern=r"^[0-9a-f]{64}$")
    probability_method: Literal["direct_binary", "direct_multiclass"] = "direct_binary"
    estimated_outcomes: list[str] = Field(default_factory=list)
    probability_calibration: Literal["uncalibrated"] = "uncalibrated"

    @model_validator(mode="after")
    def validate_contract(self):
        validate_sport_probabilities(self.sport, self.probabilities)
        expected_method = "direct_multiclass" if self.sport == "EPL" else "direct_binary"
        if self.probability_method != expected_method or self.estimated_outcomes:
            raise ValueError("Direct-model outputs must not be labeled as heuristic estimates")
        if self.class_order != list(outcome_classes(self.sport)):
            raise ValueError("Invalid outcome class ordering")
        if self.predicted_outcome != max(self.probabilities, key=self.probabilities.get):
            raise ValueError("Predicted class must match the highest probability")
        if self.feature_schema_version != SCHEMA_VERSION or self.model_identifier != MODEL_FAMILY:
            raise ValueError("Incompatible model/feature identifier")
        return self
