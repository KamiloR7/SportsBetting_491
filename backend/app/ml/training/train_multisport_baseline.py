"""Train first-pass outcome models for NFL, MLB, and EPL."""
import json
import pickle
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from app.ml.features.engineer_multisport_features import FEATURE_COLUMNS, chronological_split

SUPPORTED_SPORTS = {"NFL", "MLB", "EPL"}

def train_baseline(data: pd.DataFrame, sport: str):
    sport = sport.upper()
    if sport not in SUPPORTED_SPORTS:
        raise ValueError(f"Unsupported sport: {sport}")
    missing = set(FEATURE_COLUMNS + ["outcome"]) - set(data.columns)
    if missing:
        raise ValueError(f"Training data is missing columns: {', '.join(sorted(missing))}")
    train, test = chronological_split(data)
    if not data["outcome"].isin([0, 1]).all():
        raise ValueError("Outcome must be binary 0/1")
    if not np.isfinite(data[FEATURE_COLUMNS].to_numpy(dtype=float)).all():
        raise ValueError("Features must be finite numeric values")
    if train["outcome"].nunique() < 2:
        raise ValueError(f"{sport} training data must contain both outcome classes")
    model = Pipeline([("scaler", StandardScaler()), ("classifier", LogisticRegression(max_iter=1000, random_state=42))])
    model.fit(train[FEATURE_COLUMNS], train["outcome"])
    metadata = {"sport": sport, "model_type": "logistic_regression", "feature_columns": FEATURE_COLUMNS, "train_rows": len(train), "test_rows": len(test), "split": "chronological_80_20", "random_state": 42}
    metadata.update({
        "split": "chronological_nearest_80_20_whole_dates",
        "train_start": train["game_date"].min().isoformat(),
        "train_end": train["game_date"].max().isoformat(),
        "test_start": test["game_date"].min().isoformat(),
        "test_end": test["game_date"].max().isoformat(),
        "train_class_counts": {str(label): int(count) for label, count in train["outcome"].value_counts().items()},
        "test_class_counts": {str(label): int(count) for label, count in test["outcome"].value_counts().items()},
        "classes": [int(label) for label in model.classes_],
        "target": {"0": "not_home_win_including_draw", "1": "home_win"},
        "pandas_version": pd.__version__, "sklearn_version": sklearn.__version__,
    })
    return model, metadata

def save_baseline(model, metadata: dict, output_directory: Path) -> Path:
    output_directory.mkdir(parents=True, exist_ok=True)
    sport = str(metadata["sport"]).lower()
    payload = pickle.dumps(model)
    record = {**metadata, "model_sha256": hashlib.sha256(payload).hexdigest()}
    version = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()[:20]
    version_directory = output_directory / f"{sport}-{version}"
    version_directory.mkdir(exist_ok=True)
    model_path = version_directory / f"{sport}_baseline.pkl"
    metadata_path = version_directory / f"{sport}_baseline.json"
    metadata_bytes = (json.dumps({**record, "artifact_version": version}, indent=2, sort_keys=True) + "\n").encode()
    for path, content in ((model_path, payload), (metadata_path, metadata_bytes)):
        if path.exists():
            if path.read_bytes() != content:
                raise ValueError(f"Refusing to overwrite immutable artifact: {path}")
        else:
            with path.open("xb") as handle:
                handle.write(content)
    return model_path
