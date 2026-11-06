"""Controlled synthetic models exercise integration only, not production accuracy."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.ml.features.historical_sport_features import SCHEMA_VERSION, build_sport_feature_dataset
from app.ml.historical_baselines import outcome_classes
from app.ml.training.historical_match_model import save_historical_model, train_historical_model
from app.routes.prepared_predictions import router
from app.schemas.prepared_predictions import PreparedPredictionRequest
from app.services.prepared_prediction_service import (
    PredictionInterfaceError, PreparedPredictionService, TrustedHistoricalModelRegistry,
    TrustedModelSpec, get_prepared_prediction_service,
)
from backend.tests.test_historical_match_training import records

FROZEN_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def bundles(tmp_path_factory):
    root = tmp_path_factory.mktemp("trusted-interface-models")
    output = {}
    for sport in ("NFL", "MLB", "EPL"):
        rows = records(sport)
        data = build_sport_feature_dataset(rows, sport)
        model = train_historical_model(data)
        path = save_historical_model(model, root / sport)
        output[sport] = dict(rows=rows, data=data, model=model, path=path)
    return output


def payload(bundle):
    row = bundle["data"].test.iloc[0]
    features = {name: None if pd.isna(row[name]) else float(row[name])
                for name in bundle["data"].feature_columns}
    source_results = [dict(source_game_id=previous["game_id"], start_time=previous["kickoff_utc"],
                           result_available_at=previous["result_available_at"])
                      for previous in bundle["rows"]
                      if pd.Timestamp(previous["kickoff_utc"]).normalize() < row["game_date"]]
    return dict(match_id=row["game_id"], sport=row["sport"], start_time=row["start_time"].isoformat(),
                feature_as_of=row["feature_as_of"].isoformat(), model_version=bundle["model"].metadata["model_version"],
                feature_schema_version=SCHEMA_VERSION, feature_columns=list(bundle["data"].feature_columns),
                features=features, source_results=source_results)


def service_for(bundle, **kwargs):
    sport = bundle["model"].metadata["sport"]
    spec = TrustedModelSpec(bundle["path"], bundle["model"].metadata["model_version"])
    return PreparedPredictionService(TrustedHistoricalModelRegistry({sport: spec}, trusted_local=True),
                                     clock=lambda: FROZEN_TIME, **kwargs)


def client_for(service):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_prepared_prediction_service] = lambda: service
    return TestClient(app)


@pytest.mark.parametrize("sport", ["NFL", "MLB", "EPL"])
def test_valid_service_and_http_response_contract(bundles, sport):
    bundle = bundles[sport]
    request = payload(bundle)
    service = service_for(bundle)
    before = deepcopy(request)
    first = service.predict_prepared(request)
    assert service.predict_prepared(PreparedPredictionRequest.model_validate(request)) == first
    assert request == before
    response = client_for(service).post("/predictions/prepared", json=request)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["match_id"] == request["match_id"]
    assert result["sport"] == sport
    assert result["class_order"] == list(outcome_classes(sport))
    assert list(result["probabilities"]) == list(outcome_classes(sport))
    assert abs(sum(result["probabilities"].values()) - 1) <= 1e-6
    assert all(np.isfinite(p) and 0 <= p <= 1 for p in result["probabilities"].values())
    assert result["predicted_outcome"] == max(result["probabilities"], key=result["probabilities"].get)
    assert result["model_version"] == request["model_version"]
    assert result["feature_schema_version"] == SCHEMA_VERSION
    assert result["generated_at"] == "2026-01-01T00:00:00Z"
    assert result["prediction_method"] == "historical_logistic_regression"
    assert result["source"] == "trusted_local_development_artifact"
    assert result["freshness_status"] == "not_evaluated"


def test_null_and_nan_missing_history_are_preserved_for_imputation(bundles):
    request = payload(bundles["NFL"])
    request["features"] = {name: 0 if name.endswith(("_matches", "_wins", "_losses", "_ties", "_observations")) else None
                           for name in request["feature_columns"]}
    request["source_results"] = []
    service = service_for(bundles["NFL"])
    assert client_for(service).post("/predictions/prepared", json=request).status_code == 200
    request["features"]["home_opponent_win_rate"] = np.nan
    assert service.predict_prepared(request).sport == "NFL"


@pytest.mark.parametrize("mutation,code", [
    (lambda p: p.update(sport="NBA"), "invalid_request"),
    (lambda p: p.update(match_id=1), "invalid_request"),
    (lambda p: p.update(feature_schema_version="v0"), "feature_schema_mismatch"),
    (lambda p: p.update(feature_columns=p["feature_columns"][::-1]), "feature_schema_mismatch"),
    (lambda p: p["features"].pop("home_season_wins"), "invalid_features"),
    (lambda p: p["features"].update(outcome=1), "invalid_features"),
    (lambda p: p["features"].update(home_season_wins=-1), "invalid_features_or_cutoff"),
    (lambda p: p["features"].update(home_season_matches=1.5), "invalid_features_or_cutoff"),
    (lambda p: p["features"].update(home_recent5_avg_scored=np.inf), "invalid_features_or_cutoff"),
    (lambda p: p["features"].update(home_season_win_rate=1.1), "invalid_features_or_cutoff"),
    (lambda p: p["features"].update(home_season_wins=True), "invalid_request"),
    (lambda p: p["features"].update(home_season_wins="1"), "invalid_request"),
    (lambda p: p.update(feature_as_of=p["start_time"]), "invalid_features_or_cutoff"),
    (lambda p: p.update(feature_as_of="2024-01-25T17:00:00"), "invalid_request"),
    (lambda p: p.update(feature_as_of=12345), "invalid_request"),
    (lambda p: p.pop("source_results"), "invalid_request"),
    (lambda p: p.update(source_results=[]), "missing_provenance"),
    (lambda p: p["source_results"][0].update(result_available_at=p["start_time"]), "historical_cutoff_violation"),
    (lambda p: p["source_results"][0].update(result_available_at=p["source_results"][0]["start_time"]), "historical_cutoff_violation"),
    (lambda p: p["source_results"].append(p["source_results"][0]), "invalid_provenance"),
])
def test_invalid_inputs_reject_before_model_loading_or_execution(bundles, mutation, code):
    request = payload(bundles["NFL"])
    mutation(request)
    registry = Mock(spec=TrustedHistoricalModelRegistry)
    service = PreparedPredictionService(registry)
    with pytest.raises(PredictionInterfaceError) as error:
        service.predict_prepared(request)
    assert error.value.code == code
    registry.get.assert_not_called()


def test_same_utc_day_source_result_is_rejected_even_if_available(bundles):
    request = payload(bundles["NFL"])
    request["source_results"][0].update(start_time="2024-01-25T01:00:00Z", result_available_at="2024-01-25T03:00:00Z")
    with pytest.raises(PredictionInterfaceError, match="prior UTC days"):
        service_for(bundles["NFL"]).predict_prepared(request)


def test_future_training_labels_reject_before_predict_proba(bundles):
    bundle = bundles["NFL"]
    request = payload(bundle)
    request["features"] = {name: 0 if name.endswith(("_matches", "_wins", "_losses", "_ties", "_observations")) else None
                           for name in request["feature_columns"]}
    request["source_results"] = []
    request["feature_as_of"] = "2024-01-24T17:00:00Z"
    with patch.object(bundle["model"].pipeline, "predict_proba", side_effect=AssertionError("must not execute")):
        # The registry loads a separate pipeline, so inject the controlled model.
        registry = Mock(spec=TrustedHistoricalModelRegistry)
        registry.get.return_value = bundle["model"]
        with pytest.raises(PredictionInterfaceError) as error:
            PreparedPredictionService(registry).predict_prepared(request)
    assert error.value.code == "training_cutoff_violation"


def test_missing_registry_artifact_or_trust_never_falls_back(bundles, tmp_path):
    bundle = bundles["NFL"]
    request = payload(bundle)
    specs = {"NFL": TrustedModelSpec(tmp_path / "missing.pkl", request["model_version"])}
    for registry in [TrustedHistoricalModelRegistry(), TrustedHistoricalModelRegistry(specs),
                     TrustedHistoricalModelRegistry(specs, trusted_local=True)]:
        response = client_for(PreparedPredictionService(registry)).post("/predictions/prepared", json=request)
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "model_unavailable"
        assert str(tmp_path) not in response.text


def test_model_version_mismatch_is_explicit_and_precedes_loading(bundles):
    service = service_for(bundles["NFL"])
    request = payload(bundles["NFL"])
    request["model_version"] = "wrong-version"
    with patch("app.services.prepared_prediction_service.load_historical_model", side_effect=AssertionError("must not load")):
        response = client_for(service).post("/predictions/prepared", json=request)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "model_version_mismatch"


@pytest.mark.parametrize("corruption", ["schema", "checksum", "sport"])
def test_incompatible_artifacts_are_unavailable(bundles, tmp_path, corruption):
    bundle = bundles["NFL"]
    path = tmp_path / "model.pkl"
    shutil.copyfile(bundle["path"], path)
    shutil.copyfile(bundle["path"].with_suffix(".json"), path.with_suffix(".json"))
    if corruption == "checksum":
        path.write_bytes(b"corrupt")
    else:
        metadata = json.loads(path.with_suffix(".json").read_text())
        metadata["schema_version" if corruption == "schema" else "sport"] = "wrong"
        path.with_suffix(".json").write_text(json.dumps(metadata))
    request = payload(bundle)
    registry = TrustedHistoricalModelRegistry({"NFL": TrustedModelSpec(path, request["model_version"])}, trusted_local=True)
    response = client_for(PreparedPredictionService(registry)).post("/predictions/prepared", json=request)
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "model_unavailable"


def test_registry_caches_only_explicitly_selected_model(bundles):
    service = service_for(bundles["NFL"])
    from app.ml.training.historical_match_model import load_historical_model
    with patch("app.services.prepared_prediction_service.load_historical_model", wraps=load_historical_model) as load:
        service.predict_prepared(payload(bundles["NFL"]))
        service.predict_prepared(payload(bundles["NFL"]))
    assert load.call_count == 1


def test_configured_freshness_policy_missing_stale_and_boundary(bundles):
    bundle = bundles["NFL"]
    service = service_for(bundle, max_source_age=timedelta(hours=1))
    request = payload(bundle)
    with pytest.raises(PredictionInterfaceError) as error:
        service.predict_prepared(request)
    assert error.value.code == "freshness_unavailable"
    request["source_observed_at"] = "2024-01-25T15:00:00Z"
    with pytest.raises(PredictionInterfaceError) as error:
        service.predict_prepared(request)
    assert error.value.code == "stale_source"
    request["source_observed_at"] = "2024-01-25T16:00:00Z"
    assert service.predict_prepared(request).freshness_status == "within_configured_age"


@pytest.mark.parametrize("observed", ["2024-01-25T18:00:00Z", "2024-01-01T01:00:00Z"])
def test_invalid_source_observation_chronology(bundles, observed):
    request = payload(bundles["NFL"])
    request["source_observed_at"] = observed
    with pytest.raises(PredictionInterfaceError) as error:
        service_for(bundles["NFL"]).predict_prepared(request)
    assert error.value.code == "invalid_source_timestamp"


def test_invalid_model_output_is_controlled_and_no_private_error_details(bundles):
    bundle = bundles["NFL"]
    registry = Mock(spec=TrustedHistoricalModelRegistry)
    registry.get.return_value = bundle["model"]
    service = PreparedPredictionService(registry)
    output = bundle["model"].predict(bundle["data"].test.iloc[[0]], schema_version=SCHEMA_VERSION)[0]
    output["probabilities"] = {"home_win": 0.9, "away_win": 0.9}
    with patch.object(bundle["model"], "predict", return_value=[output]):
        response = client_for(service).post("/predictions/prepared", json=payload(bundle))
    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "prediction_failed"


def test_route_validation_errors_are_structured_for_fields_and_bad_json(bundles):
    client = client_for(service_for(bundles["NFL"]))
    for response in [client.post("/predictions/prepared", json={"match_id": 1}),
                     client.post("/predictions/prepared", content="{", headers={"Content-Type": "application/json"})]:
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "invalid_request"
        assert response.json()["detail"]["errors"]


def test_main_registers_prepared_route_without_changing_legacy_routes(monkeypatch):
    for key, value in {"DATABASE_HOST": "localhost", "DATABASE_PORT": "5432", "DATABASE_NAME": "test_db",
                       "DATABASE_USER": "test_user", "DATABASE_PASSWORD": "test_password"}.items():
        monkeypatch.setenv(key, value)
    from app.main import app
    paths = set(app.openapi()["paths"])
    assert {"/predictions", "/predictions/matches/{match_id}", "/predictions/prepared"} <= paths
    # ID-only requests cannot masquerade as resolved feature records.
    client = TestClient(app)
    result = client.post("/predictions/prepared", json={"match_id": "1"})
    assert result.status_code == 422
    assert result.json()["detail"]["code"] == "invalid_request"


def test_unknown_model_request_paths_or_extra_fields_are_forbidden(bundles):
    request = payload(bundles["NFL"])
    request["model_path"] = "/tmp/untrusted.pkl"
    response = client_for(service_for(bundles["NFL"])).post("/predictions/prepared", json=request)
    assert response.status_code == 422


def test_bad_service_configuration_is_rejected(bundles):
    with pytest.raises(ValueError):
        service_for(bundles["NFL"], max_source_age=timedelta(0))
    with pytest.raises(ValueError):
        TrustedHistoricalModelRegistry({"NBA": TrustedModelSpec(Path("none"), "v1")}, trusted_local=True)



def test_future_feature_cutoff_is_rejected_before_loading(bundles):
    request = payload(bundles["NFL"])
    request.update(start_time="2030-01-02T18:00:00Z", feature_as_of="2030-01-02T17:00:00Z")
    registry = Mock(spec=TrustedHistoricalModelRegistry)
    with pytest.raises(PredictionInterfaceError) as error:
        PreparedPredictionService(registry, clock=lambda: FROZEN_TIME).predict_prepared(request)
    assert error.value.code == "future_feature_cutoff"
    registry.get.assert_not_called()


@pytest.mark.parametrize("field,value", [("home_season_wins", 100), ("home_venue_matches", 100),
                                         ("home_recent5_matches", 2), ("home_recent5_avg_margin", 123)])
def test_contradictory_features_are_rejected_before_loading(bundles, field, value):
    request = payload(bundles["NFL"])
    request["features"][field] = value
    registry = Mock(spec=TrustedHistoricalModelRegistry)
    with pytest.raises(PredictionInterfaceError) as error:
        PreparedPredictionService(registry).predict_prepared(request)
    assert error.value.code == "invalid_feature_consistency"
    registry.get.assert_not_called()


def test_mutated_request_model_is_revalidated(bundles):
    request = PreparedPredictionRequest.model_validate(payload(bundles["NFL"]))
    request.sport = "NBA"
    with pytest.raises(PredictionInterfaceError) as error:
        service_for(bundles["NFL"]).predict_prepared(request)
    assert error.value.code == "invalid_request"


def test_naive_prediction_clock_is_unavailable_before_loading(bundles):
    registry = Mock(spec=TrustedHistoricalModelRegistry)
    service = PreparedPredictionService(registry, clock=lambda: datetime(2026, 1, 1))
    with pytest.raises(PredictionInterfaceError) as error:
        service.predict_prepared(payload(bundles["NFL"]))
    assert error.value.code == "prediction_unavailable"
    registry.get.assert_not_called()


def test_default_application_does_not_expose_a_synthetic_model(bundles, monkeypatch):
    for key, value in {"DATABASE_HOST": "localhost", "DATABASE_PORT": "5432", "DATABASE_NAME": "test_db",
                       "DATABASE_USER": "test_user", "DATABASE_PASSWORD": "test_password"}.items():
        monkeypatch.setenv(key, value)
    from app.main import app
    response = TestClient(app).post("/predictions/prepared", json=payload(bundles["NFL"]))
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "model_unavailable"


def test_mapping_insertion_order_does_not_change_declared_feature_order(bundles):
    request = payload(bundles["EPL"])
    service = service_for(bundles["EPL"])
    first = service.predict_prepared(request)
    request["features"] = dict(reversed(list(request["features"].items())))
    assert service.predict_prepared(request) == first
