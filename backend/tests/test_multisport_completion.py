import hashlib
import json
import pickle

import numpy as np
import pandas as pd
import pytest

from app.ml.features.prepare_multisport_data import validate_games
from app.ml.features.engineer_multisport_features import create_features, chronological_split, FEATURE_COLUMNS
from app.ml.features.download_multisport_data import normalize_mlb, normalize_epl, normalize_nfl
from app.ml.training.train_multisport_baseline import save_baseline, train_baseline
from app.ml.evaluation.evaluate_multisport_models import evaluate_model
from app.ml.run_multisport_pipeline import run_pipeline
from app.ml.predict_multisport import load_trusted_baseline, predict_outcomes


def games(count=20):
    return pd.DataFrame([
        {"game_id": str(index), "game_date": f"2024-01-{index + 1:02d}",
         "home_team": "A" if index % 2 else "B", "away_team": "B" if index % 2 else "A",
         "home_score": index % 3, "away_score": 1}
        for index in range(count)
    ])


@pytest.mark.parametrize("column,value", [
    ("game_date", None), ("game_date", "invalid"), ("game_id", " "),
    ("home_team", ""), ("home_team", None), ("home_score", -1),
    ("home_score", float("inf")), ("home_score", float("nan")),
    ("home_score", "bad"), ("home_score", 1.5),
])
def test_invalid_records_rejected(column, value):
    records = games().to_dict("records")
    records[0][column] = value
    with pytest.raises((ValueError, TypeError)):
        validate_games("NFL", pd.DataFrame(records))


def test_numeric_scores_are_normalized():
    data = games()
    data["home_score"] = data["home_score"].astype(str)
    assert validate_games("MLB", data)["home_score"].dtype.kind in "iu"


@pytest.mark.parametrize("data", [pd.DataFrame(), games(1), games(2).assign(game_date="2024-01-01")])
def test_unsplittable_data_rejected(data):
    with pytest.raises(ValueError):
        chronological_split(data)


def test_split_keeps_same_day_together_and_parses_dates():
    data = games(10)
    data.loc[7:9, "game_date"] = "2024-01-08"
    train, test = chronological_split(data)
    assert train["game_date"].max() < test["game_date"].min()
    assert len(train) == 7
    assert set(train.game_id).isdisjoint(test.game_id)


def test_same_day_and_future_scores_cannot_change_earlier_features():
    data = games(8)
    data.loc[1, "game_date"] = data.loc[0, "game_date"]
    before = create_features(data)
    changed = data.copy()
    changed.loc[1:, "home_score"] = 100
    after = create_features(changed)
    pd.testing.assert_frame_equal(before.loc[:1, FEATURE_COLUMNS], after.loc[:1, FEATURE_COLUMNS])
    assert before.loc[:1, FEATURE_COLUMNS].to_numpy().sum() == 0


def test_future_mutation_does_not_change_training_features():
    data = games()
    before = create_features(data)
    data.loc[16:, "away_score"] = 100
    after = create_features(data)
    pd.testing.assert_frame_equal(before.loc[:15, FEATURE_COLUMNS], after.loc[:15, FEATURE_COLUMNS])


def test_draw_is_not_an_away_win_label():
    features = create_features(games(1).assign(home_score=1, away_score=1))
    assert features.outcome.tolist() == [0]


def test_model_round_trip_and_versions(tmp_path):
    features = create_features(games())
    model, metadata = train_baseline(features, "NFL")
    metadata["dataset_sha256"] = "first"
    first = save_baseline(model, metadata, tmp_path)
    assert save_baseline(model, metadata, tmp_path) == first
    restored = pickle.loads(first.read_bytes())
    np.testing.assert_array_equal(model.predict_proba(features[FEATURE_COLUMNS]),
                                  restored.predict_proba(features[FEATURE_COLUMNS]))
    metadata["dataset_sha256"] = "second"
    assert save_baseline(model, metadata, tmp_path) != first
    assert first.exists()
    first.write_bytes(b"damaged")
    metadata["dataset_sha256"] = "first"
    with pytest.raises(ValueError, match="overwrite"):
        save_baseline(model, metadata, tmp_path)
    with pytest.raises(ValueError, match="checksum"):
        load_trusted_baseline(first)


def test_prediction_contract(tmp_path):
    data = create_features(games())
    model, metadata = train_baseline(data, "EPL")
    loaded, _ = load_trusted_baseline(save_baseline(model, metadata, tmp_path))
    result = predict_outcomes(loaded, data)
    assert set(result.columns) == {"predicted_outcome", "probability_not_home_win", "probability_home_win"}
    np.testing.assert_allclose(result.iloc[:, 1:].sum(axis=1), 1)
    for invalid in (data.drop(columns=FEATURE_COLUMNS[0]), data.iloc[:0],
                    data.assign(home_win_rate=2), data.assign(home_avg_score=float("nan"))):
        with pytest.raises(ValueError):
            predict_outcomes(loaded, invalid)


def test_evaluation_contains_probability_quality_and_baseline():
    data = create_features(games())
    model, _ = train_baseline(data, "EPL")
    metrics = evaluate_model(model, data)
    assert 0 <= metrics["brier_score"] <= 1
    assert metrics["log_loss"] >= 0
    assert sum(bin_result["count"] for bin_result in metrics["calibration_bins"]) == metrics["test_rows"]
    assert "training_prevalence_baseline" in metrics


def test_training_scaler_only_sees_training_partition():
    data = create_features(games())
    data.loc[16:, FEATURE_COLUMNS] = 999.0
    model, _ = train_baseline(data, "NFL")
    train, _ = chronological_split(data)
    np.testing.assert_allclose(model.named_steps["scaler"].mean_, train[FEATURE_COLUMNS].mean())


@pytest.mark.parametrize("change", ["single_class", "bad_label", "nonfinite"])
def test_invalid_training_inputs(change):
    data = create_features(games())
    if change == "single_class":
        data["outcome"] = 1
    elif change == "bad_label":
        data.loc[0, "outcome"] = 2
    else:
        data.loc[0, FEATURE_COLUMNS[0]] = float("inf")
    with pytest.raises(ValueError):
        train_baseline(data, "MLB")


def mlb_game(identifier=1):
    return {"gamePk": identifier, "officialDate": "2024-04-01", "gameType": "R",
            "status": {"detailedState": "Final"},
            "teams": {"home": {"team": {"id": 1}, "score": 3},
                      "away": {"team": {"id": 2}, "score": 1}}}


def test_mlb_filters_postponed_resumed_and_duplicates():
    final = mlb_game()
    postponed = {**mlb_game(2), "status": {"detailedState": "Postponed"}}
    resumed = {**mlb_game(3), "resumeDate": "2024-04-02"}
    data, counts = normalize_mlb(json.dumps({"dates": [{"games": [final, final, postponed, resumed]}]}).encode())
    assert data.game_id.tolist() == ["1"]
    assert sum(counts["excluded"].values()) == 3


def test_mlb_conflicting_duplicate_fails():
    first, second = mlb_game(), mlb_game()
    second["teams"]["home"]["score"] = 5
    with pytest.raises(ValueError, match="Conflicting"):
        normalize_mlb(json.dumps({"dates": [{"games": [first, second]}]}).encode())


def test_epl_maps_day_first_dates_and_scores():
    data, _ = normalize_epl(b"Div,Date,HomeTeam,AwayTeam,FTHG,FTAG\nE0,12/08/2024,A,B,2,2\n", "2425")
    assert data.game_date.iloc[0].month == 8
    assert data.home_score.iloc[0] == 2
    assert data.game_id.iloc[0].startswith("EPL-2425-")


def test_nfl_filters_seasons_postseason_and_missing_scores():
    data = games(4).rename(columns={"game_date": "gameday"})
    data["season"] = [2023, 2024, 2022, 2024]
    data["game_type"] = ["REG", "POST", "REG", "REG"]
    data.loc[3, "home_score"] = None
    result, _ = normalize_nfl(data.to_csv(index=False).encode())
    assert result.game_id.astype(str).tolist() == ["0"]


def test_full_pipeline_offline_and_provenance_guard(tmp_path):
    raw, output = tmp_path / "raw", tmp_path / "models"
    raw.mkdir()
    provenance = {"sports": {}}
    for sport in ("NFL", "MLB", "EPL"):
        path = raw / f"{sport.lower()}_games.csv"
        games().to_csv(path, index=False)
        provenance["sports"][sport] = {"dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    (raw / "provenance.json").write_text(json.dumps(provenance))
    report = run_pipeline(raw, output)
    assert set(report["sports"]) == {"NFL", "MLB", "EPL"}
    assert all(result["reload_predictions_identical"] for result in report["sports"].values())
    assert (output / "report.json").exists()
    with (raw / "nfl_games.csv").open("a") as handle:
        handle.write("\n")
    with pytest.raises(ValueError, match="provenance"):
        run_pipeline(raw, output)
