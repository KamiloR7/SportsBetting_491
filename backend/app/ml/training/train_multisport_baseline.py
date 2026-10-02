"""Train first-pass outcome models for NFL, MLB, and EPL."""
import json
import pickle
from pathlib import Path
import pandas as pd
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
    if train["outcome"].nunique() < 2:
        raise ValueError(f"{sport} training data must contain both outcome classes")
    model = Pipeline([("scaler", StandardScaler()), ("classifier", LogisticRegression(max_iter=1000, random_state=42))])
    model.fit(train[FEATURE_COLUMNS], train["outcome"])
    metadata = {"sport": sport, "model_type": "logistic_regression", "feature_columns": FEATURE_COLUMNS, "train_rows": len(train), "test_rows": len(test), "split": "chronological_80_20", "random_state": 42}
    return model, metadata

def save_baseline(model, metadata: dict, output_directory: Path) -> Path:
    output_directory.mkdir(parents=True, exist_ok=True)
    sport = str(metadata["sport"]).lower()
    model_path = output_directory / f"{sport}_baseline.pkl"
    with model_path.open("wb") as handle:
        pickle.dump(model, handle)
    (output_directory / f"{sport}_baseline.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return model_path
