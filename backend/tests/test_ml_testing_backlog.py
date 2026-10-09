import json

import numpy as np
import pandas as pd
import pytest

from app.ml.evaluation.evaluate_multisport_models import evaluate_model
from app.ml.features.download_multisport_data import normalize_epl, normalize_mlb
from app.ml.features.engineer_multisport_features import (
    FEATURE_COLUMNS,
    chronological_split,
    create_features,
)
from app.ml.features.prepare_multisport_data import validate_games
from app.ml.predict_multisport import predict_outcomes
from app.ml.training.train_multisport_baseline import train_baseline


def dated_games(dates: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "game_id": f"g-{index}",
                "game_date": game_date,
                "home_team": "A" if index % 2 == 0 else "B",
                "away_team": "B" if index % 2 == 0 else "A",
                "home_score": 2 if index % 3 else 0,
                "away_score": 1,
            }
            for index, game_date in enumerate(dates)
        ]
    )


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("game_id", "g-1", "duplicate game_id"),
        ("game_date", "not-a-date", "not-a-date"),
        ("home_team", "A", "Teams must be distinct"),
        ("away_score", None, "missing teams or final scores"),
    ],
)
def test_real_data_contract_rejects_common_provider_edge_cases(column, value, message):
    data = dated_games([f"2024-01-{day:02d}" for day in range(1, 7)])
    if column == "game_id":
        data.loc[1, column] = "g-0"
    elif column == "home_team":
        data.loc[0, "away_team"] = data.loc[0, "home_team"]
    else:
        data.loc[0, column] = value

    with pytest.raises((ValueError, TypeError), match=message):
        validate_games("NFL", data)


def test_mlb_resumed_and_nonfinal_games_are_excluded_from_regression_fixture():
    final = {
        "gamePk": 100,
        "officialDate": "2024-04-01",
        "gameType": "R",
        "status": {"detailedState": "Final"},
        "teams": {
            "home": {"team": {"id": 1}, "score": 5},
            "away": {"team": {"id": 2}, "score": 3},
        },
    }
    resumed = {**final, "gamePk": 101, "resumeDate": "2024-04-02"}
    postponed = {**final, "gamePk": 102, "status": {"detailedState": "Postponed"}}

    normalized, counts = normalize_mlb(
        json.dumps({"dates": [{"games": [final, resumed, postponed]}]}).encode()
    )

    assert normalized["game_id"].tolist() == ["100"]
    assert counts["excluded"]["resumed_game_leakage_guard"] == 1
    assert counts["excluded"]["not_completed_regular_season"] == 1


def test_epl_draws_remain_not_home_win_in_prediction_training_label():
    normalized, _ = normalize_epl(
        b"Div,Date,HomeTeam,AwayTeam,FTHG,FTAG\nE0,12/08/2024,A,B,2,2\n",
        "2425",
    )

    features = create_features(normalized)

    assert features["outcome"].tolist() == [0]


def test_chronological_split_keeps_large_same_day_batch_out_of_train_boundary():
    data = dated_games(
        [
            "2024-01-01",
            "2024-01-02",
            "2024-01-03",
            "2024-01-04",
            "2024-01-05",
            "2024-01-06",
            "2024-01-07",
            "2024-01-08",
            "2024-01-08",
            "2024-01-08",
        ]
    )

    train, test = chronological_split(create_features(data))

    assert train["game_date"].max() < test["game_date"].min()
    assert set(data.loc[data["game_date"] == "2024-01-08", "game_id"]).issubset(
        set(test["game_id"])
    )


def test_future_result_mutation_does_not_change_prior_day_features_across_sports():
    dates = [f"2024-01-{day:02d}" for day in range(1, 13)]
    base = dated_games(dates)
    mutated = base.copy()
    mutated.loc[8:, ["home_score", "away_score"]] = [99, 0]

    before = create_features(base)
    after = create_features(mutated)

    pd.testing.assert_frame_equal(
        before.loc[:7, FEATURE_COLUMNS],
        after.loc[:7, FEATURE_COLUMNS],
    )


def test_prediction_contract_rejects_extra_bad_columns_but_ignores_safe_extras():
    data = create_features(dated_games([f"2024-01-{day:02d}" for day in range(1, 21)]))
    model, _ = train_baseline(data, "NFL")
    with_extra = data.assign(display_team="A")

    result = predict_outcomes(model, with_extra)

    assert list(result.columns) == [
        "predicted_outcome",
        "probability_not_home_win",
        "probability_home_win",
    ]
    np.testing.assert_allclose(
        result["probability_not_home_win"] + result["probability_home_win"],
        1.0,
    )

    with pytest.raises(ValueError, match="finite and nonnegative"):
        predict_outcomes(model, data.assign(home_avg_allowed=-1))


def test_model_evaluation_report_contains_threshold_review_fields():
    data = create_features(dated_games([f"2024-01-{day:02d}" for day in range(1, 25)]))
    model, _ = train_baseline(data, "MLB")

    metrics = evaluate_model(model, data)

    assert {"accuracy", "precision", "recall", "f1", "brier_score", "log_loss"}.issubset(
        metrics
    )
    assert len(metrics["calibration_bins"]) == 5
    assert metrics["training_prevalence_baseline"]["accuracy"] >= 0
    assert metrics["probability_mean_sum"] == pytest.approx(1.0)
