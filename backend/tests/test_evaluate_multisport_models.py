import pandas as pd
import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.ml.evaluation.evaluate_multisport_models import evaluate_model, model_version, write_evaluation
from app.ml.features.engineer_multisport_features import FEATURE_COLUMNS


def test_model_version_is_stable():
    metadata = {"sport": "NFL", "model_type": "logistic_regression"}
    assert model_version(metadata, "abc") == model_version(metadata, "abc")
    assert model_version(metadata, "abc") != model_version(metadata, "def")


def test_writes_versioned_evaluation(tmp_path):
    path = write_evaluation(tmp_path, "MLB", {"accuracy": 0.5}, {"sport": "MLB"}, "abc123")
    content = path.read_text()
    assert '"sport": "MLB"' in content
    assert '"model_version": "sprint2-model-' in content


def test_evaluates_held_out_predictions():
    data = pd.DataFrame([
        {"game_id": str(index), "game_date": f"2025-01-{index + 1:02d}",
         "outcome": index % 2,
         **{feature: float(index % 2) for feature in FEATURE_COLUMNS}}
        for index in range(10)
    ])
    model = make_pipeline(StandardScaler(), LogisticRegression(random_state=42))
    model.fit(data.iloc[:8][FEATURE_COLUMNS], data.iloc[:8]["outcome"])
    metrics = evaluate_model(model, data)
    assert metrics["test_rows"] == 2
    assert metrics["accuracy"] == 1.0
    assert metrics["probability_mean_sum"] == pytest.approx(1.0)


@pytest.mark.parametrize("probabilities", [
    [[float("nan"), 0.5]], [[-0.1, 1.1]], [[0.2, 0.2]], [[1.0]],
])
def test_rejects_invalid_probabilities(probabilities):
    class InvalidModel:
        def predict(self, features):
            return np.zeros(len(features), dtype=int)

        def predict_proba(self, features):
            return np.tile(probabilities, (len(features), 1))

    data = pd.DataFrame([
        {"game_id": str(index), "game_date": f"2025-01-{index + 1:02d}",
         "outcome": 0, **{feature: 0.0 for feature in FEATURE_COLUMNS}}
        for index in range(5)
    ])
    with pytest.raises(ValueError):
        evaluate_model(InvalidModel(), data)
