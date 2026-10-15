import json

import pandas as pd
import pytest

from app.ml.features.engineer_multisport_features import create_features
from app.ml.training.train_multisport_baseline import save_baseline, train_baseline
from app.services.model_registry import (
    ModelConfigurationError,
    ModelNotFoundError,
    ModelRegistry,
)


def _games(count=20):
    return create_features(
        pd.DataFrame(
            [
                {
                    "game_id": str(index),
                    "game_date": f"2024-01-{index + 1:02d}",
                    "home_team": "A" if index % 2 else "B",
                    "away_team": "B" if index % 2 else "A",
                    "home_score": index % 3,
                    "away_score": 1,
                }
                for index in range(count)
            ]
        )
    )


def _write_models(directory):
    paths = {}
    features = _games()
    for sport in ("NFL", "MLB", "EPL"):
        model, metadata = train_baseline(features, sport)
        paths[sport] = save_baseline(model, metadata, directory)
    return paths


def test_discovers_loads_and_caches_all_sport_models(tmp_path):
    paths = _write_models(tmp_path)
    registry = ModelRegistry.from_directory(tmp_path)

    loaded = registry.load_all()

    assert set(loaded) == {"NFL", "MLB", "EPL"}
    assert registry.get(" nfl ") is loaded["NFL"]
    assert all(metadata["sport"] == sport for sport, (_, metadata) in loaded.items())
    assert all(paths[sport].is_file() for sport in loaded)


def test_missing_sport_artifact_is_reported(tmp_path):
    with pytest.raises(ModelNotFoundError, match="No deployed model found"):
        ModelRegistry.from_directory(tmp_path)


def test_multiple_versions_require_explicit_selection(tmp_path):
    paths = _write_models(tmp_path)
    duplicate = tmp_path / "nfl-second-version"
    duplicate.mkdir()
    duplicate_path = duplicate / "nfl_baseline.pkl"
    duplicate_path.write_bytes(paths["NFL"].read_bytes())

    with pytest.raises(ModelConfigurationError, match="Multiple deployed models.*NFL"):
        ModelRegistry.from_directory(tmp_path)


def test_metadata_must_match_configured_sport(tmp_path):
    paths = _write_models(tmp_path)
    nfl_metadata = paths["NFL"].with_suffix(".json")
    metadata = json.loads(nfl_metadata.read_text())
    metadata["sport"] = "MLB"
    nfl_metadata.write_text(json.dumps(metadata))

    registry = ModelRegistry({"NFL": paths["NFL"]})
    with pytest.raises(ModelConfigurationError, match="contains 'MLB' metadata"):
        registry.get("NFL")


def test_unsupported_sport_is_rejected(tmp_path):
    registry = ModelRegistry({})

    with pytest.raises(ModelConfigurationError, match="Unsupported sport"):
        registry.get("NBA")
