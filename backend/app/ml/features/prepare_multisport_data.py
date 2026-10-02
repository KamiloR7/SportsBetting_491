"""Validate real NFL, MLB, and EPL match datasets for Sprint 2."""

from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    sport: {"game_id", "game_date", "home_team", "away_team", "home_score", "away_score"}
    for sport in ("NFL", "MLB", "EPL")
}


def load_and_validate_dataset(sport: str, path: Path) -> pd.DataFrame:
    """Load one sport dataset and validate the shared match contract."""
    sport = sport.upper()
    if sport not in REQUIRED_COLUMNS:
        raise ValueError(f"Unsupported sport: {sport}. Expected NFL, MLB, or EPL.")
    if not path.exists():
        raise FileNotFoundError(f"{sport} dataset was not found: {path}")

    data = pd.read_csv(path)
    missing = REQUIRED_COLUMNS[sport] - set(data.columns)
    if missing:
        raise ValueError(f"{sport} dataset is missing required columns: {', '.join(sorted(missing))}")
    data = data.copy()
    data["game_date"] = pd.to_datetime(data["game_date"], errors="raise", utc=True)
    if data.empty:
        raise ValueError(f"{sport} dataset is empty: {path}")
    if data["game_id"].isna().any() or data["game_id"].duplicated().any():
        raise ValueError(f"{sport} dataset contains missing or duplicate game_id values")
    if data[["home_team", "away_team", "home_score", "away_score"]].isna().any().any():
        raise ValueError(f"{sport} dataset contains missing teams or final scores")
    return data.sort_values("game_date").reset_index(drop=True)


def load_all_datasets(raw_directory: Path = Path("data/raw")) -> dict[str, pd.DataFrame]:
    """Load the three Sprint 2 datasets from the checked-in data contract."""
    return {
        sport: load_and_validate_dataset(sport, raw_directory / f"{sport.lower()}_games.csv")
        for sport in REQUIRED_COLUMNS
    }
