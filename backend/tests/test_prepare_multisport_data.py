from pathlib import Path

import pandas as pd
import pytest

from app.ml.features.prepare_multisport_data import load_and_validate_dataset


def row() -> dict:
    return {"game_id": "game-1", "game_date": "2025-09-01", "home_team": "Home", "away_team": "Away", "home_score": 21, "away_score": 17}


@pytest.mark.parametrize("sport", ["NFL", "MLB", "EPL"])
def test_loads_each_supported_sport(sport: str, tmp_path: Path) -> None:
    path = tmp_path / f"{sport.lower()}_games.csv"
    pd.DataFrame([row()]).to_csv(path, index=False)
    result = load_and_validate_dataset(sport, path)
    assert len(result) == 1
    assert result.loc[0, "game_date"].year == 2025


def test_rejects_missing_required_column(tmp_path: Path) -> None:
    value = row()
    del value["away_score"]
    path = tmp_path / "nfl_games.csv"
    pd.DataFrame([value]).to_csv(path, index=False)
    with pytest.raises(ValueError, match="missing required columns"):
        load_and_validate_dataset("NFL", path)


def test_rejects_duplicate_game_ids(tmp_path: Path) -> None:
    path = tmp_path / "epl_games.csv"
    pd.DataFrame([row(), row()]).to_csv(path, index=False)
    with pytest.raises(ValueError, match="duplicate game_id"):
        load_and_validate_dataset("EPL", path)
