"""Canonical prepared-input evidence; no raw input values are logged."""
from datetime import timezone
import hashlib
import json
import math

from app.schemas.prepared_predictions import PreparedPredictionRequest


def canonical_prediction_input_hash(request: PreparedPredictionRequest) -> str:
    """Hash semantic model inputs, excluding processing time and response data.

    Call after request/preflight validation. Normalize equivalent UTC instants,
    mapping/evidence ordering, numeric representations and supported null/NaN
    missingness. Declared feature order remains significant.
    """
    def instant(value):
        return value.astimezone(timezone.utc).isoformat(timespec="microseconds")

    def numeric(value):
        if value is None or math.isnan(float(value)):
            return None
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("Cannot hash non-finite non-missing features")
        return 0.0 if result == 0 else result

    record = {
        "canonicalization": "prepared_input_v1", "match_id": request.match_id,
        "sport": request.sport, "start_time": instant(request.start_time),
        "feature_as_of": instant(request.feature_as_of),
        "feature_schema_version": request.feature_schema_version,
        "feature_columns": list(request.feature_columns),
        "feature_values": [numeric(request.features[name]) for name in request.feature_columns],
        "model_version": request.model_version,
        "source_observed_at": instant(request.source_observed_at) if request.source_observed_at else None,
        "source_results": sorted([
            {"source_game_id": result.source_game_id.strip(), "start_time": instant(result.start_time),
             "result_available_at": instant(result.result_available_at)}
            for result in request.source_results
        ], key=lambda item: (item["source_game_id"], item["start_time"], item["result_available_at"])),
    }
    encoded = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()
