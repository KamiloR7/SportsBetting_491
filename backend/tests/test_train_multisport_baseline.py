import pandas as pd
import pytest
from app.ml.features.engineer_multisport_features import FEATURE_COLUMNS
from app.ml.training.train_multisport_baseline import save_baseline, train_baseline

def training_data():
    return pd.DataFrame([{**{"game_id": str(i), "game_date": f"2025-01-{i + 1:02d}", "outcome": i % 2}, **{f: float(i + 1) for f in FEATURE_COLUMNS}} for i in range(12)])

@pytest.mark.parametrize("sport", ["NFL", "MLB", "EPL"])
def test_trains_each_supported_sport(sport):
    model, metadata = train_baseline(training_data(), sport)
    assert metadata["sport"] == sport
    assert model.predict_proba(training_data()[FEATURE_COLUMNS]).shape == (12, 2)

def test_rejects_unsupported_sport():
    with pytest.raises(ValueError, match="Unsupported sport"):
        train_baseline(training_data(), "NBA")

def test_saves_model_and_metadata(tmp_path):
    model, metadata = train_baseline(training_data(), "NFL")
    path = save_baseline(model, metadata, tmp_path)
    assert path.exists()
    assert path.with_suffix(".json").exists()
