"""Executed P1 assessment on controlled synthetic fixtures, not a compliance certificate."""
from copy import deepcopy
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from app.ml.features.historical_sport_features import SCHEMA_VERSION, build_sport_feature_dataset
from app.ml.probability_validation import validate_sport_probabilities
from app.schemas.prepared_predictions import PreparedPredictionRequest
from app.services.prediction_input_integrity import canonical_prediction_input_hash
from app.services.prepared_prediction_service import PreparedPredictionService, TrustedHistoricalModelRegistry, TrustedModelSpec
from backend.tests.test_prepared_prediction_interface import bundles, payload, client_for
from backend.tests.test_historical_match_training import records


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def cold_start(request):
    result = deepcopy(request)
    result["features"] = {name: 0 if name.endswith(("_matches", "_wins", "_losses", "_ties", "_draws", "_observations")) else None
                          for name in result["feature_columns"]}
    result["source_results"] = []
    return result


def upcoming_service(bundle, **kwargs):
    request = payload(bundle)
    spec = TrustedModelSpec(bundle["path"], request["model_version"])
    registry = TrustedHistoricalModelRegistry({request["sport"]: spec}, trusted_local=True)
    clock = pd.Timestamp(request["feature_as_of"]).to_pydatetime()
    return PreparedPredictionService(registry, clock=lambda: clock, **kwargs)


@pytest.fixture(scope="module")
def assessment():
    report = {"evidence_version": 1, "synthetic_fixtures_only": True,
              "proposal_source": "Exact P1 acceptance criteria supplied by Kamilo Ramirez in conversation",
              "invalid_scenarios": [], "consistency": [], "leakage": [], "freshness": [], "transparency": []}
    yield report
    output = os.environ.get("P1_EVIDENCE_OUTPUT")
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
        events = [dict(event="invalid_input_rejected", scenario_id=row["id"], status=row["actual_status"],
                       error_code=row["actual_code"], model_executions=row["model_executions"])
                  for row in sorted(report["invalid_scenarios"], key=lambda item: item["id"])]
        path.with_suffix(".jsonl").write_text("".join(json.dumps(event, sort_keys=True) + "\n" for event in events))


SCENARIOS = [
    ("P1.1-01", "unsupported sport", 422, "invalid_request"),
    ("P1.1-02", "missing required feature", 422, "invalid_features"),
    ("P1.1-03", "incorrect numeric type", 422, "invalid_request"),
    ("P1.1-04", "infinite scoring value", 422, "invalid_features_or_cutoff"),
    ("P1.1-05", "incorrect feature ordering", 409, "feature_schema_mismatch"),
    ("P1.1-06", "feature schema mismatch", 409, "feature_schema_mismatch"),
    ("P1.1-07", "model version mismatch", 409, "model_version_mismatch"),
    ("P1.1-08", "cutoff at kickoff", 422, "invalid_features_or_cutoff"),
    ("P1.1-09", "future historical result", 422, "historical_cutoff_violation"),
    ("P1.1-10", "stale upcoming source", 422, "stale_source"),
    ("P1.1-11", "blank match identity", 422, "invalid_request"),
    ("P1.1-12", "unsupported prediction configuration", 422, "invalid_request"),
]


def invalid_request(request, scenario):
    request = deepcopy(request)
    if scenario == "P1.1-01": request["sport"] = "NBA"
    elif scenario == "P1.1-02": request["features"].pop("home_recent5_avg_scored")
    elif scenario == "P1.1-03": request["features"]["home_season_wins"] = "one"
    elif scenario == "P1.1-04": request["features"]["home_recent5_avg_scored"] = float("inf")
    elif scenario == "P1.1-05": request["feature_columns"].reverse()
    elif scenario == "P1.1-06": request["feature_schema_version"] = "incompatible-v0"
    elif scenario == "P1.1-07": request["model_version"] = "not-configured"
    elif scenario == "P1.1-08": request["feature_as_of"] = request["start_time"]
    elif scenario == "P1.1-09": request["source_results"][0]["result_available_at"] = request["start_time"]
    elif scenario == "P1.1-10":
        request = cold_start(request)
        request["source_observed_at"] = (pd.Timestamp(request["feature_as_of"]) - timedelta(hours=24, microseconds=1)).isoformat()
    elif scenario == "P1.1-11": request["match_id"] = " "
    elif scenario == "P1.1-12": request["prediction_method"] = "unapproved_baseline_fallback"
    return request


@pytest.mark.parametrize("scenario,title,status,code", SCENARIOS, ids=[row[0] for row in SCENARIOS])
def test_p1_1_twelve_http_rejections_precede_model_execution(bundles, assessment, scenario, title, status, code):
    bundle = bundles["NFL"]
    request = payload(bundle)
    request["source_observed_at"] = request["feature_as_of"]
    service = upcoming_service(bundle)
    model = service.registry.get("NFL", request["model_version"])
    if scenario == "P1.1-08":
        # Isolate pre-kickoff validation rather than the earlier processing-time guard.
        service.clock = lambda: pd.Timestamp(request["start_time"]).to_pydatetime()
    # Spy on both inference entry and the actual sklearn prediction operation.
    with patch.object(model, "predict", wraps=model.predict) as inference:
        with patch.object(model.pipeline, "predict_proba", wraps=model.pipeline.predict_proba) as execute:
            response = client_for(service).post("/predictions/prepared", content=json.dumps(invalid_request(request, scenario)),
                                                headers={"Content-Type": "application/json"})
    body = response.json()
    actual_code = body.get("detail", {}).get("code")
    row = dict(id=scenario, scenario=title, expected_status=status, expected_code=code,
               actual_status=response.status_code, actual_code=actual_code,
               model_executions=execute.call_count, inference_calls=inference.call_count,
               prediction_generated="probabilities" in body or "predicted_outcome" in body)
    assessment["invalid_scenarios"].append(row)
    assert response.status_code == status and actual_code == code
    assert execute.call_count == 0 and inference.call_count == 0
    assert not row["prediction_generated"]
    assert isinstance(body["detail"]["message"], str)


@pytest.mark.parametrize("sport", ["NFL", "MLB", "EPL"])
def test_p1_3_ten_accepted_executions_preserve_hash_order_model_and_probabilities(bundles, assessment, sport):
    bundle = bundles[sport]
    request = payload(bundle)
    request["source_observed_at"] = request["feature_as_of"]
    service = upcoming_service(bundle)
    model = service.registry.get(sport, request["model_version"])
    with patch.object(model.pipeline, "predict_proba", wraps=model.pipeline.predict_proba) as execute:
        results = [client_for(service).post("/predictions/prepared", json=request) for _ in range(10)]
    assert execute.call_count == 10
    orders = {tuple(call.args[0].columns) for call in execute.call_args_list}
    assert orders == {tuple(request["feature_columns"])}
    assert all(result.status_code == 200 for result in results)
    bodies = [result.json() for result in results]
    hashes = {result["input_sha256"] for result in bodies}
    versions = {result["model_version"] for result in bodies}
    probabilities = {digest(result["probabilities"]) for result in bodies}
    for result in bodies:
        validate_sport_probabilities(sport, result["probabilities"])
        assert result["freshness_status"] == "within_configured_age"
        assert result["source_freshness_limit_seconds"] == 86400
    assert len(hashes) == len(versions) == len(orders) == len(probabilities) == 1
    expected_hash = canonical_prediction_input_hash(PreparedPredictionRequest.model_validate(request))
    assert hashes == {expected_hash}
    assessment["consistency"].append(dict(
        sport=sport, execution_count=len(bodies), model_executions=execute.call_count, unique_input_hashes=len(hashes), input_sha256=expected_hash,
        ordered_schema_sha256=digest(request["feature_columns"]), unique_feature_orders=len(orders),
        unique_model_versions=len(versions), model_version=next(iter(versions)),
        unique_probability_vectors=len(probabilities), reference_probabilities=bodies[0]["probabilities"],
        probability_sum_tolerance=0.000001, all_probabilities_valid=True,
    ))


def test_hash_normalizes_order_offsets_and_null_nan_without_hiding_feature_changes(bundles):
    first = payload(bundles["NFL"])
    second = deepcopy(first)
    second["features"] = dict(reversed(list(second["features"].items())))
    second["source_results"].reverse()
    second["feature_as_of"] = pd.Timestamp(first["feature_as_of"]).tz_convert("America/Los_Angeles").isoformat()
    second["features"]["home_opponent_win_rate"] = np.nan
    a = canonical_prediction_input_hash(PreparedPredictionRequest.model_validate(first))
    assert a == canonical_prediction_input_hash(PreparedPredictionRequest.model_validate(second))
    second["features"]["home_season_wins"] += 1
    assert a != canonical_prediction_input_hash(PreparedPredictionRequest.model_validate(second))


@pytest.mark.parametrize("case", ["same_day", "future_record", "target_record", "unavailable_result"])
def test_p1_2_adversarial_history_evidence_never_reaches_model(bundles, assessment, case):
    bundle = bundles["NFL"]
    request = payload(bundle)
    request["source_observed_at"] = request["feature_as_of"]
    row = request["source_results"][0]
    if case == "same_day": row.update(start_time="2024-01-25T01:00:00Z", result_available_at="2024-01-25T03:00:00Z")
    elif case == "future_record": row.update(start_time="2030-01-01T00:00:00Z", result_available_at="2030-01-01T04:00:00Z")
    elif case == "target_record": row["source_game_id"] = request["match_id"]
    else: row["result_available_at"] = request["start_time"]
    service = upcoming_service(bundle)
    model = service.registry.get("NFL", request["model_version"])
    with patch.object(model.pipeline, "predict_proba", wraps=model.pipeline.predict_proba) as execute:
        response = client_for(service).post("/predictions/prepared", json=request)
    assert response.status_code == 422 and execute.call_count == 0
    assessment["leakage"].append(dict(case=case, rejected=True, model_executions=execute.call_count,
                                      actual_code=response.json()["detail"]["code"]))


def test_p1_2_future_score_invariance_and_rolling_eligibility(bundles, assessment):
    bundle = bundles["NFL"]
    original = bundle["data"]
    changed_rows = records("NFL")
    changed_rows[-1]["home_score"] = 100
    changed = build_sport_feature_dataset(changed_rows, "NFL")
    pd.testing.assert_frame_equal(original.test[original.feature_columns], changed.test[changed.feature_columns])
    assert bundle["model"].predict(original.test, schema_version=SCHEMA_VERSION) == bundle["model"].predict(changed.test, schema_version=SCHEMA_VERSION)
    assert original.test.iloc[0].home_season_matches == 24
    assert original.test.iloc[1].home_season_matches == 25
    changed_rows[0]["result_available_at"] = changed_rows[-1]["result_available_at"]
    with pytest.raises(ValueError, match="unavailable"):
        build_sport_feature_dataset(changed_rows, "NFL")
    assessment["leakage"].append(dict(case="future_score_and_rolling_history", invariant=True,
                                      unavailable_prior_result_rejected=True))


@pytest.mark.parametrize("age,expected", [(None, 422), (timedelta(hours=24), 200),
                                          (timedelta(hours=24, microseconds=1), 422),
                                          (timedelta(hours=23, minutes=59), 200)])
def test_upcoming_24_hour_policy_boundaries(bundles, assessment, age, expected):
    bundle = bundles["NFL"]
    request = cold_start(payload(bundle))
    if age is not None:
        request["source_observed_at"] = (pd.Timestamp(request["feature_as_of"]) - age).isoformat()
    response = client_for(upcoming_service(bundle)).post("/predictions/prepared", json=request)
    assert response.status_code == expected
    assessment["freshness"].append(dict(case="missing" if age is None else str(age), expected_status=expected,
                                        actual_status=response.status_code,
                                        result=response.json().get("detail", {}).get("code", "within_configured_age")))


def test_upcoming_old_feature_cutoff_does_not_bypass_processing_time_freshness(bundles):
    bundle = bundles["NFL"]
    request = cold_start(payload(bundle))
    request["start_time"] = "2024-02-01T18:00:00Z"
    request["source_observed_at"] = request["feature_as_of"]
    service = upcoming_service(bundle)
    service.clock = lambda: pd.Timestamp("2024-01-30T17:00:00Z").to_pydatetime()
    response = client_for(service).post("/predictions/prepared", json=request)
    assert response.status_code == 422 and response.json()["detail"]["code"] == "stale_source"


def test_upcoming_policy_cannot_be_weakened_and_nan_history_remains_valid(bundles):
    bundle = bundles["NFL"]
    request = cold_start(payload(bundle))
    request["source_observed_at"] = (pd.Timestamp(request["feature_as_of"]) - timedelta(hours=25)).isoformat()
    response = client_for(upcoming_service(bundle, max_source_age=timedelta(days=7))).post("/predictions/prepared", json=request)
    assert response.status_code == 422 and response.json()["detail"]["code"] == "stale_source"
    request["source_observed_at"] = request["feature_as_of"]
    request["features"]["home_opponent_win_rate"] = np.nan
    result = upcoming_service(bundle).predict_prepared(request)
    assert result.source_freshness_limit_seconds == 86400
    assert result.source_freshness_reference == "prediction_time"


def test_p1_4_direct_epl_is_not_mislabeled_as_estimated(bundles, assessment):
    bundle = bundles["EPL"]
    request = payload(bundle)
    request["source_observed_at"] = request["feature_as_of"]
    result = upcoming_service(bundle).predict_prepared(request)
    assert result.probability_method == "direct_multiclass"
    assert result.estimated_outcomes == [] and result.probability_calibration == "uncalibrated"
    assessment["transparency"].append(dict(path="prepared", method=result.probability_method,
        estimated_outcomes=result.estimated_outcomes, calibration=result.probability_calibration))


def test_p1_4_legacy_estimated_epl_is_disclosed_and_unsupported_sport_fails(assessment):
    from app.services.match_prediction import predict_probabilities
    from backend.tests.test_predictions import FakeBinaryModel, final_match
    history = [final_match(10, 20, 1, 1), final_match(20, 10, 2, 0)]
    with patch("app.services.match_prediction.model_artifact", return_value="synthetic-local-only.pkl"):
        with patch("app.services.match_prediction.load_trusted_baseline", return_value=(FakeBinaryModel(), {"sport": "EPL"})):
            result = predict_probabilities("EPL", 10, 20, history)
    assert result["probability_method"] == "estimated_epl_split"
    assert result["estimated_outcomes"] == ["draw", "away_win"]
    assert result["probability_calibration"] == "uncalibrated"
    assessment["transparency"].append(dict(path="legacy_estimated", method=result["probability_method"],
        estimated_outcomes=result["estimated_outcomes"], calibration=result["probability_calibration"]))
    with pytest.raises(ValueError, match="Unsupported"):
        predict_probabilities("NBA", 10, 20, history)



def test_legacy_estimate_api_carries_sport_and_disclosure_for_frontend():
    from app.routes.predictions import run_match_prediction
    from backend.tests.test_predictions import FakeBinaryModel, final_match, mock_db, scheduled_match
    history = [final_match(10, 20, 1, 1), final_match(20, 10, 2, 0)]
    with patch("app.services.match_prediction.model_artifact", return_value="synthetic-local-only.pkl"):
        with patch("app.services.match_prediction.load_trusted_baseline", return_value=(FakeBinaryModel(), {"sport": "EPL"})):
            response = run_match_prediction(match_id=7, db=mock_db(scheduled_match("EPL"), history))
    assert response.sport == "EPL"
    assert response.probability_method == "estimated_epl_split"
    assert response.estimated_outcomes == ["draw", "away_win"]
    assert response.probability_calibration == "uncalibrated"
