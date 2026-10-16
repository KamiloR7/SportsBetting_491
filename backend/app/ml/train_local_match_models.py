"""Train local baseline artifacts from completed database matches."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from app.database.db import engine
from app.ml.features.engineer_multisport_features import create_features
from app.ml.training.train_multisport_baseline import save_baseline, train_baseline

DEFAULT_OUTPUT = Path(__file__).resolve().parents[3] / "build" / "sprint2-models"


def completed_games(conn, sport: str) -> pd.DataFrame:
    rows = conn.execute(
        text(
            """
            SELECT m.id, m.start_time, ht.name AS home_team, at.name AS away_team,
                   m.home_score, m.away_score
            FROM matches m
            JOIN leagues l ON l.id = m.league_id
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE l.abbreviation = :sport
              AND m.status = 'final'
              AND m.home_score IS NOT NULL
              AND m.away_score IS NOT NULL
            ORDER BY m.start_time, m.id
            """
        ),
        {"sport": sport},
    ).all()
    return pd.DataFrame([{
        "game_id": str(row.id),
        "game_date": row.start_time.isoformat() if hasattr(row.start_time, "isoformat") else row.start_time,
        "home_team": row.home_team,
        "away_team": row.away_team,
        "home_score": row.home_score,
        "away_score": row.away_score,
    } for row in rows])


def train_local_models(output: Path = DEFAULT_OUTPUT, source_engine=engine) -> dict[str, Path]:
    artifacts = {}
    with source_engine.connect() as conn:
        for sport in ("NFL", "MLB", "EPL"):
            games = completed_games(conn, sport)
            if games.empty:
                raise ValueError(f"No completed {sport} matches are available for training.")
            features = create_features(games)
            model, metadata = train_baseline(features, sport)
            metadata["training_source"] = "local_database"
            artifacts[sport] = save_baseline(model, metadata, output)
    return artifacts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    for league, path in train_local_models(arguments.output).items():
        print(f"{league}: {path}")
