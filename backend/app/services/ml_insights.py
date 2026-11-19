"""Read-only public evidence for evaluations and match feature reconstruction."""
import hashlib
import json
from app.services.prediction_service import MatchHistoryRepository

REPORT_FIELDS = ("schema_version", "generated_at", "source_generated_at", "data_cutoff", "method", "sports", "unavailable")
SPORT_FIELDS = ("sport", "model_version", "model_type", "classes", "dataset_sha256", "snapshot_verified",
                "train_rows", "test_rows", "train_start", "train_end", "test_start", "test_end",
                "baseline_outcome", "baseline_accuracy", "accuracy", "correct", "log_loss",
                "confusion_matrix", "calibration_bins", "expected_calibration_error")


def read_evaluation(directory):
    manifest = (directory / "manifest.json").read_bytes()
    report = json.loads((directory / "evaluation.json").read_text(encoding="utf-8"))
    if report["schema_version"] != 1 or report["manifest_sha256"] != hashlib.sha256(manifest).hexdigest():
        raise ValueError("Evaluation report does not match the configured model snapshot")
    result = {key: report[key] for key in REPORT_FIELDS}
    result["sports"] = [{key: item[key] for key in SPORT_FIELDS} for item in report["sports"]]
    result["unavailable"] = [{"sport": item["sport"], "reason": "The saved holdout could not be reproduced. Rebuild and verify its evaluation report."} for item in report["unavailable"]]
    for item in result["sports"]:
        count, classes, matrix = item["test_rows"], item["classes"], item["confusion_matrix"]
        if count <= 0 or len(matrix) != len(classes) or any(len(row) != len(classes) for row in matrix):
            raise ValueError("Invalid confusion matrix")
        if sum(map(sum, matrix)) != count or sum(b["count"] for b in item["calibration_bins"]) != count:
            raise ValueError("Invalid evaluation counts")
    return result


def match_inputs(db, match_id, registry=None):
    context = MatchHistoryRepository(db).get_context(match_id)
    model = None
    if registry is not None:
        try:
            _, metadata = registry.get(context.sport)
            from pandas import Timestamp
            model = {"version": metadata["artifact_version"], "training_end": metadata["train_end"],
                     "eligible_for_target": Timestamp(metadata["train_end"]) < Timestamp(context.feature_cutoff)}
        except (OSError, ValueError, KeyError, TypeError):
            pass
    return {"match_id": context.match_id, "sport": context.sport,
            "feature_cutoff": context.feature_cutoff.isoformat(),
            "history_scope": "all_available_completed_prior_UTC_days",
            "source": "current_database_reconstruction", "model": model,
            "units": {"NFL": "points", "MLB": "runs", "EPL": "goals"}[context.sport],
            "teams": [{"side": side, "name": getattr(context, f"{side}_team_name"),
                       "history_games": getattr(context, f"{side}_history_games"),
                       "win_rate": context.features[f"{side}_win_rate"],
                       "avg_score": context.features[f"{side}_avg_score"],
                       "avg_allowed": context.features[f"{side}_avg_allowed"]} for side in ("home", "away")]}
