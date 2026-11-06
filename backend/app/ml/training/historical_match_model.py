"""Train-only preprocessing and versioned logistic regression for historical sport features."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import pickle
import platform

import numpy as np
import pandas as pd
import sklearn
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.ml.features.historical_sport_features import SCHEMA_VERSION, SportFeatureDataset, feature_columns
from app.ml.historical_baselines import BaselinePredictor, InsufficientHistoryError, METHODS, outcome_classes
from app.ml.probability_validation import validate_sport_probabilities
from app.ml.training.train_multisport_baseline import save_baseline

MODEL_FAMILY = "historical_logistic_regression_v1"
CLASSIFIER_CONFIG = {"C": 1.0, "max_iter": 1000, "random_state": 42, "solver": "lbfgs", "tol": 0.0001}
PREPROCESSING_CONFIG = {
    "imputer": "median", "keep_empty_features": True,
    "add_indicator": True, "scaler": "standard",
}
_ARTIFACT_FIELDS = {"model_sha256", "artifact_version"}


def _versions():
    return {"python": platform.python_version(), "numpy": np.__version__,
            "pandas": pd.__version__, "sklearn": sklearn.__version__}


def _version(metadata):
    record = {key: value for key, value in metadata.items()
              if key not in _ARTIFACT_FIELDS | {"model_version"}}
    digest = hashlib.sha256(json.dumps(record, sort_keys=True, allow_nan=False).encode()).hexdigest()
    return f"historical-logreg-{digest[:20]}"


def _matrix(frame: pd.DataFrame, sport: str) -> pd.DataFrame:
    columns = feature_columns(sport)
    if not isinstance(frame, pd.DataFrame) or frame.empty or not frame.columns.is_unique:
        raise ValueError("Expected nonempty features with unique column names")
    missing = set(columns) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing model feature columns: {sorted(missing)}")
    for column in columns:
        values = frame[column]
        if (not pd.api.types.is_numeric_dtype(values) or pd.api.types.is_bool_dtype(values)
                or pd.api.types.is_complex_dtype(values)):
            raise ValueError(f"{column} must contain real numeric values, not strings or booleans")
    matrix = frame.loc[:, columns].astype(float)
    if np.isinf(matrix.to_numpy()).any():
        raise ValueError("Infinite feature values are invalid; missing history must be NaN")
    for column in columns:
        values = matrix[column]
        counts = column.endswith(("_matches", "_wins", "_losses", "_draws", "_ties", "_observations"))
        if counts:
            if values.isna().any() or (values < 0).any() or (values % 1 != 0).any():
                raise ValueError(f"{column} must contain finite nonnegative integer counts")
        elif not column.endswith("_avg_margin") and (values < 0).any():
            raise ValueError(f"{column} must be nonnegative or NaN")
        if column.endswith("_win_rate") and (values > 1).any():
            raise ValueError(f"{column} must not exceed one")
        if column.endswith("_points_per_match") and (values > 3).any():
            raise ValueError(f"{column} must not exceed three")
    return matrix


def _fitted_state_digest(pipeline):
    """Fingerprint numeric fitted state independently of pickle memoization."""
    imputer, scaler, classifier = (pipeline.named_steps[name] for name in ("imputer", "scaler", "classifier"))
    digest = hashlib.sha256()
    for values in (imputer.statistics_, imputer.indicator_.features_, scaler.mean_,
                   scaler.scale_, scaler.var_, classifier.coef_, classifier.intercept_):
        array = np.ascontiguousarray(values)
        digest.update(json.dumps([array.dtype.str, list(array.shape)]).encode())
        digest.update(array.tobytes())
    return digest.hexdigest()


def _check_metadata(metadata):
    try:
        sport = metadata["sport"]
        if (metadata["model_family"] != MODEL_FAMILY
                or metadata["schema_version"] != SCHEMA_VERSION
                or metadata["feature_columns"] != feature_columns(sport)
                or metadata["class_order"] != list(outcome_classes(sport))
                or metadata["classifier_classes"] != sorted(outcome_classes(sport))
                or metadata["versions"] != _versions()
                or metadata["classifier_config"] != CLASSIFIER_CONFIG
                or metadata["preprocessing"] != PREPROCESSING_CONFIG
                or not isinstance(metadata["fitted_state_sha256"], str)
                or len(metadata["fitted_state_sha256"]) != 64
                or metadata["model_version"] != _version(metadata)):
            raise ValueError("Incompatible model metadata, schema, configuration or software version")
        minimum = metadata["min_samples_per_class"]
        counts = metadata["class_counts"]
        if (type(minimum) is not int or minimum < 1
                or len(counts) != len(outcome_classes(sport))
                or any(type(value) is not int or value < minimum for value in counts)
                or metadata["fit_rows"] != sum(counts)
                or type(metadata["excluded_training_ties"]) is not int
                or metadata["excluded_training_ties"] < 0):
            raise ValueError("Invalid training counts in model metadata")
        end = pd.Timestamp(metadata["training_end_day"])
        available = pd.Timestamp(metadata["training_labels_available_at"])
        if end.tzinfo is None or available.tzinfo is None or available <= end or end != end.normalize():
            raise ValueError("Invalid training cutoffs in model metadata")
    except (KeyError, TypeError) as exc:
        raise ValueError("Missing or invalid model metadata") from exc


def _check_pipeline(pipeline, metadata):
    if (not isinstance(pipeline, Pipeline)
            or list(pipeline.named_steps) != ["imputer", "scaler", "classifier"]
            or not isinstance(pipeline.named_steps["imputer"], SimpleImputer)
            or not isinstance(pipeline.named_steps["scaler"], StandardScaler)
            or not isinstance(pipeline.named_steps["classifier"], LogisticRegression)):
        raise ValueError("Unexpected serialized model pipeline")
    imputer = pipeline.named_steps["imputer"]
    classifier = pipeline.named_steps["classifier"]
    scaler = pipeline.named_steps["scaler"]
    required = [(pipeline, "feature_names_in_"), (imputer, "statistics_"),
                (scaler, "n_features_in_"), (classifier, "coef_"), (classifier, "classes_")]
    if not all(hasattr(step, name) for step, name in required):
        raise ValueError("Unfitted or incompatible model pipeline")
    if (list(pipeline.feature_names_in_) != metadata["feature_columns"]
            or list(classifier.classes_) != metadata["classifier_classes"]
            or imputer.strategy != "median" or not imputer.keep_empty_features or not imputer.add_indicator
            or not scaler.with_mean or not scaler.with_std
            or imputer.n_features_in_ != len(metadata["feature_columns"])
            or scaler.n_features_in_ != len(imputer.get_feature_names_out())
            or classifier.n_features_in_ != scaler.n_features_in_
            or not np.isfinite(classifier.coef_).all() or not np.isfinite(classifier.intercept_).all()
            or any(classifier.get_params()[key] != value for key, value in CLASSIFIER_CONFIG.items())
            or _fitted_state_digest(pipeline) != metadata["fitted_state_sha256"]):
        raise ValueError("Model pipeline does not match recorded schema/classes/configuration")


def _guard(metadata):
    return BaselinePredictor(
        sport=metadata["sport"], class_counts=tuple(metadata["class_counts"]),
        training_end_day=pd.Timestamp(metadata["training_end_day"]),
        labels_available_at=pd.Timestamp(metadata["training_labels_available_at"]),
        excluded_training_ties=metadata["excluded_training_ties"],
    )


@dataclass
class HistoricalMatchModel:
    pipeline: Pipeline
    metadata: dict

    def predict(self, frame: pd.DataFrame, *, schema_version: str) -> list[dict]:
        """Predict after training with explicit, stable outcome class ordering."""
        _check_metadata(self.metadata)
        _check_pipeline(self.pipeline, self.metadata)
        # Reuse match identity, pre-kickoff and training-label availability guards.
        _guard(self.metadata).predict(frame, METHODS[0], schema_version=schema_version)
        matrix = _matrix(frame, self.metadata["sport"])
        probabilities = self.pipeline.predict_proba(matrix)
        classes = self.metadata["class_order"]
        if probabilities.shape != (len(frame), len(classes)):
            raise ValueError("Invalid prediction probability shape")
        indices = [list(self.pipeline.classes_).index(label) for label in classes]
        output = []
        for index, match_id in enumerate(frame["game_id"]):
            scores = {label: float(probabilities[index, column]) for label, column in zip(classes, indices)}
            validate_sport_probabilities(self.metadata["sport"], scores)
            output.append({
                "match_id": match_id, "sport": self.metadata["sport"],
                "predicted_outcome": max(scores, key=scores.get), "probabilities": scores,
                "class_order": list(classes), "model_identifier": MODEL_FAMILY,
                "model_version": self.metadata["model_version"],
                "feature_schema_version": self.metadata["schema_version"],
            })
        return output


def train_historical_model(dataset: SportFeatureDataset, *, min_samples_per_class: int = 2) -> HistoricalMatchModel:
    """Fit only labeled training rows; never inspect test values or labels."""
    if type(min_samples_per_class) is not int or min_samples_per_class < 1:
        raise ValueError("min_samples_per_class must be a positive integer")
    guard = BaselinePredictor.fit(dataset)
    if any(count < min_samples_per_class for count in guard.class_counts):
        raise InsufficientHistoryError("Training requires every supported outcome class and sufficient samples per class")
    matrix = _matrix(dataset.train, guard.sport)
    labeled = dataset.train["outcome"].notna()
    pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median", keep_empty_features=True, add_indicator=True)),
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(**CLASSIFIER_CONFIG)),
    ])
    pipeline.fit(matrix.loc[labeled], dataset.train.loc[labeled, "outcome"])
    if (pipeline.named_steps["classifier"].n_iter_ >= CLASSIFIER_CONFIG["max_iter"]).any():
        raise ValueError("Logistic regression failed to converge")
    # JSON's Python float representation keeps full precision; NaN here is a
    # deterministic internal digest marker, not published evaluation evidence.
    training_bytes = json.dumps(dataset.train.to_dict("records"), sort_keys=True, default=str).encode()
    metadata = {
        "model_family": MODEL_FAMILY, "sport": guard.sport, "schema_version": SCHEMA_VERSION,
        "feature_columns": list(dataset.feature_columns), "class_order": list(outcome_classes(guard.sport)),
        "classifier_classes": list(pipeline.classes_), "classifier_config": dict(CLASSIFIER_CONFIG),
        "preprocessing": dict(PREPROCESSING_CONFIG), "versions": _versions(),
        "min_samples_per_class": min_samples_per_class, "class_counts": list(guard.class_counts),
        "fit_rows": int(labeled.sum()), "excluded_training_ties": guard.excluded_training_ties,
        "training_end_day": guard.training_end_day.isoformat(),
        "training_labels_available_at": guard.labels_available_at.isoformat(),
        "training_data_sha256": hashlib.sha256(training_bytes).hexdigest(),
        "fitted_state_sha256": _fitted_state_digest(pipeline),
    }
    metadata["model_version"] = _version(metadata)
    _check_metadata(metadata)
    _check_pipeline(pipeline, metadata)
    return HistoricalMatchModel(pipeline=pipeline, metadata=metadata)


def save_historical_model(model: HistoricalMatchModel, directory: Path) -> Path:
    """Reuse immutable, checksummed project artifacts; do not commit generated files."""
    _check_metadata(model.metadata)
    _check_pipeline(model.pipeline, model.metadata)
    metadata = {key: value for key, value in model.metadata.items() if key not in _ARTIFACT_FIELDS}
    return save_baseline(model.pipeline, metadata, Path(directory))


def load_historical_model(path: Path, *, trusted_local: bool = False) -> HistoricalMatchModel:
    """Only load artifacts already established as trusted by the caller.

    Pickle executes code. A checksum and this flag do not establish authenticity.
    Never opt in for downloaded, uploaded, or otherwise untrusted artifacts.
    """
    if trusted_local is not True:
        raise ValueError("Refusing to deserialize an untrusted model; require explicit trusted_local=True")
    path = Path(path)
    metadata = json.loads(path.with_suffix(".json").read_text())
    _check_metadata(metadata)  # Check compatibility before any deserialization.
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != metadata.get("model_sha256"):
        raise ValueError("Model checksum mismatch")
    pipeline = pickle.loads(payload)
    _check_pipeline(pipeline, metadata)
    return HistoricalMatchModel(pipeline=pipeline, metadata=metadata)
