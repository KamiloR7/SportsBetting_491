import pandas as pd
import pytest

from app.ml.features.engineer_multisport_features import (
    FEATURE_COLUMNS,
)
from app.ml.training.train_multisport_baseline import (
    save_baseline,
    train_baseline,
)
from app.ml.probability_validation import validate_probabilities


def training_data():
    return pd.DataFrame([
        {
            **{
                "game_id": str(i),
                "game_date": f"2025-01-{i + 1:02d}",
                "outcome": i % 2,
            },
            **{f: float(i + 1) for f in FEATURE_COLUMNS},
        }
        for i in range(12)
    ])


# =====================================
# Existing baseline training tests
# =====================================

@pytest.mark.parametrize("sport", ["NFL", "MLB", "EPL"])
def test_trains_each_supported_sport(sport):
    model, metadata = train_baseline(training_data(), sport)

    assert metadata["sport"] == sport

    assert model.predict_proba(
        training_data()[FEATURE_COLUMNS]
    ).shape == (12, 2)


def test_rejects_unsupported_sport():
    with pytest.raises(ValueError, match="Unsupported sport"):
        train_baseline(training_data(), "NBA")


def test_saves_model_and_metadata(tmp_path):
    model, metadata = train_baseline(training_data(), "NFL")

    path = save_baseline(model, metadata, tmp_path)

    assert path.exists()
    assert path.with_suffix(".json").exists()


# =====================================
# Sprint 3: ML probability validation
# =====================================

@pytest.mark.parametrize("sport", ["NFL", "MLB", "EPL"])
def test_trained_model_produces_valid_probabilities(sport):
    """
    Verify the trained baseline model produces valid
    probability distributions for each supported sport.
    """

    data = training_data()

    # Train the existing baseline model.
    model, metadata = train_baseline(data, sport)

    # Obtain actual probabilities from the model.
    predictions = model.predict_proba(
        data[FEATURE_COLUMNS]
    )

    # Existing baseline uses two outcome classes.
    assert predictions.shape == (len(data), 2)

    # Verify model metadata.
    assert metadata["sport"] == sport
    assert set(model.classes_) == {0, 1}

    # Validate each model-generated distribution.
    for prediction in predictions:
        probabilities = {
            "not_home_win" if int(label) == 0 else "home_win":
                float(probability)
            for label, probability in zip(
                model.classes_, prediction
            )
        }

        assert validate_probabilities(probabilities)