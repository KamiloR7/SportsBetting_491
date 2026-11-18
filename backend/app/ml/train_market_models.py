"""Evaluate outcome models on a chronological holdout, then fit deployable prices.
Run from backend: python -m app.ml.train_market_models
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import accuracy_score, log_loss
from app.database.db import engine
from app.ml.train_local_match_models import completed_games
from app.ml.features.sport_aware_features import create_sport_aware_features
from app.ml.features.engineer_multisport_features import chronological_split, FEATURE_COLUMNS
from app.ml.training.train_sport_aware_baseline import train_sport_aware_baseline
from app.ml.training.train_multisport_baseline import save_baseline
from app.core.config import settings


def main():
    output = settings.MARKET_MODEL_DIRECTORY
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"generated_at": datetime.now(timezone.utc).isoformat(), "sports": {}}
    cutoff = pd.Timestamp.now(tz="UTC").normalize()
    with engine.connect() as conn:
        for sport in ("NFL", "MLB", "EPL"):
            games = completed_games(conn, sport)
            games = games.loc[pd.to_datetime(games.game_date, utc=True).dt.normalize() < cutoff]
            frame = create_sport_aware_features(games, sport)
            train, test = chronological_split(frame)
            evaluated, metadata = train_sport_aware_baseline(frame, sport)
            metrics = {"accuracy": float(accuracy_score(test.outcome, evaluated.predict(test[FEATURE_COLUMNS]))),
                       "log_loss": float(log_loss(test.outcome, evaluated.predict_proba(test[FEATURE_COLUMNS]), labels=list(evaluated.classes_))),
                       "test_rows": len(test), "train_rows": len(train),
                       "majority_baseline_accuracy": float((test.outcome == train.outcome.mode().iloc[0]).mean()),
                       "train_end": train.game_date.max().isoformat(), "test_start": test.game_date.min().isoformat()}
            deployed = clone(evaluated).fit(frame[FEATURE_COLUMNS], frame.outcome)
            metadata.update({"training_source": "local_real_match_database", "train_rows": len(frame),
                             "train_end": frame.game_date.max().isoformat(), "deployment_fit": "all_completed_prior_UTC_days",
                             "train_class_counts": {str(label): int(count) for label, count in frame.outcome.value_counts().items()},
                             "test_rows": 0, "split": "deployment_refit_all_prior_UTC_days",
                             "pipeline_version": "model_odds_v1",
                             "dataset_sha256": hashlib.sha256(frame.to_csv(index=False).encode()).hexdigest(),
                             "holdout_evaluation_before_refit": metrics})
            metadata.pop("test_start", None)
            metadata.pop("test_end", None)
            path = save_baseline(deployed, metadata, output)
            manifest["sports"][sport] = {"artifact": str(path.relative_to(output)), "metrics": metrics,
                                          "classes": list(deployed.classes_), "training_rows": len(frame)}
            print(sport, json.dumps(manifest["sports"][sport]), flush=True)
    temporary = output / "manifest.next.json"
    temporary.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output / "manifest.json")

if __name__ == "__main__": main()
