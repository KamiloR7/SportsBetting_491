"""Isolated synthetic Sprint 3 backend for local UI review without PostgreSQL.

Run from backend/: python -m uvicorn app.database.demo:app --port 8000
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.db import get_db
from app.database.seed_data import seed_leagues, seed_sports, seed_teams
from app.database.seed_dev_matches import run_seed
from app.main import app
from app.ml.train_local_match_models import train_local_models

demo_engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
demo_sessions = sessionmaker(bind=demo_engine)
model_dir = Path(__file__).resolve().parents[3] / "build" / "sprint3-demo-models"


def prepare_demo() -> None:
    with demo_engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE sports (id INTEGER PRIMARY KEY, name TEXT, slug TEXT UNIQUE)")
        conn.exec_driver_sql("""
            CREATE TABLE leagues (
                id INTEGER PRIMARY KEY, sport_id INTEGER, name TEXT,
                abbreviation TEXT, country TEXT, active BOOLEAN DEFAULT 1
            )
        """)
        conn.exec_driver_sql("""
            CREATE TABLE teams (
                id INTEGER PRIMARY KEY, sport_id INTEGER, name TEXT,
                abbreviation TEXT, city TEXT, active BOOLEAN DEFAULT 1
            )
        """)
        conn.exec_driver_sql("""
            CREATE TABLE matches (
                id INTEGER PRIMARY KEY, league_id INTEGER, home_team_id INTEGER,
                away_team_id INTEGER, start_time TEXT NOT NULL, status TEXT,
                home_score INTEGER, away_score INTEGER, neutral_site BOOLEAN DEFAULT 0
            )
        """)
        sport_ids = seed_sports(conn)
        seed_leagues(conn, sport_ids)
        seed_teams(conn, sport_ids)
    run_seed(demo_engine)
    train_local_models(model_dir, demo_engine)
    os.environ["PREDICTION_MODEL_DIR"] = str(model_dir)


def demo_db():
    with demo_sessions() as session:
        yield session


prepare_demo()
app.title = "Sports Match Prediction API (Synthetic Demo)"
app.dependency_overrides[get_db] = demo_db
