"""Opt-in integration tests. Never use the application's configured database.

Requires DATA25_DISPOSABLE_POSTGRES_URL with database name exactly
sportsbetting_data25_test and DATA25_ALLOW_DISPOSABLE_TEST=1. Each test creates
and removes only its own random schema. No connection is made by default.
"""
import os
from pathlib import Path
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.database.historical_import import load_historical_matches
from backend.tests.test_historical_import import record


@pytest.fixture
def postgres():
    value = os.environ.get("DATA25_DISPOSABLE_POSTGRES_URL")
    if not value or os.environ.get("DATA25_ALLOW_DISPOSABLE_TEST") != "1":
        pytest.skip("No explicitly authorized disposable PostgreSQL test database")
    url = make_url(value)
    if url.get_backend_name() != "postgresql" or url.database != "sportsbetting_data25_test" or url.host not in {"localhost", "127.0.0.1", "::1"}:
        pytest.fail("Integration tests require a local sportsbetting_data25_test database")
    schema = "data25_" + uuid4().hex
    bootstrap = create_engine(url)
    engine = None
    try:
        with bootstrap.begin() as conn:
            conn.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
        engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
        ddl = (Path(__file__).parents[1] / "app/database/sports_prediction_schema.sql").read_text()
        ddl = ddl.replace("BEGIN;", "").replace("COMMIT;", "")
        with engine.begin() as conn:
            conn.exec_driver_sql(ddl)
            for sport, slug, league, season in [
                ("American Football", "american-football", "NFL", "2024"),
                ("Baseball", "baseball", "MLB", "2024"),
                ("Soccer", "soccer", "EPL", "2024-25"),
            ]:
                sport_id = conn.execute(text("INSERT INTO sports(name,slug) VALUES (:name,:slug) RETURNING id"), {"name": sport, "slug": slug}).scalar_one()
                league_id = conn.execute(text("INSERT INTO leagues(sport_id,name,abbreviation) VALUES (:sport,:name,:name) RETURNING id"), {"sport": sport_id, "name": league}).scalar_one()
                conn.execute(text("INSERT INTO seasons(league_id,name) VALUES (:league,:name)"), {"league": league_id, "name": season})
                for name, abbr in [("Home", "H"), ("Away", "A")]:
                    conn.execute(text("INSERT INTO teams(sport_id,name,abbreviation) VALUES (:sport,:name,:abbr)"), {"sport": sport_id, "name": name, "abbr": abbr})
        yield engine
    finally:
        if engine is not None:
            engine.dispose()
        with bootstrap.begin() as conn:
            conn.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        bootstrap.dispose()


def test_postgres_reimport_correction_and_doubleheader(postgres):
    rows = [record("NFL", game_id="nfl", home_score=1), record("EPL", game_id="epl", home_score=1),
            record("MLB", game_id="mlb1"), record("MLB", game_id="mlb2")]
    assert load_historical_matches(postgres, rows)["matches_inserted"] == 4
    with postgres.connect() as conn:
        ids = conn.execute(text("SELECT id FROM matches ORDER BY id")).scalars().all()
    assert load_historical_matches(postgres, rows)["matches_updated"] == 4
    result = load_historical_matches(postgres, [record("MLB", game_id="mlb1", home_score=7, kickoff_utc="2024-09-01T21:00:00Z")])
    assert result["matches_updated"] == 1
    with postgres.connect() as conn:
        assert conn.execute(text("SELECT id FROM matches ORDER BY id")).scalars().all() == ids
        assert conn.execute(text("SELECT count(*) FROM matches WHERE season_id IS NOT NULL AND neutral_site")).scalar_one() == 4
        assert conn.execute(text("SELECT count(*) FROM external_mappings WHERE entity_type='match'")).scalar_one() == 4
        assert conn.execute(text("SELECT count(*) FROM matches WHERE home_score=7")).scalar_one() == 1


def test_postgres_forced_failure_rolls_back_batch(postgres):
    with postgres.begin() as conn:
        conn.exec_driver_sql("""CREATE FUNCTION fail_test_match() RETURNS trigger AS $$
          BEGIN IF NEW.home_score = 99 THEN RAISE EXCEPTION 'forced test failure'; END IF;
          RETURN NEW; END; $$ LANGUAGE plpgsql""")
        conn.exec_driver_sql("CREATE TRIGGER fail_test BEFORE INSERT ON matches FOR EACH ROW EXECUTE FUNCTION fail_test_match()")
    report = load_historical_matches(postgres, [record(game_id="first"), record(game_id="second", home_score=99)])
    assert report["transaction_failures"] and report["matches_inserted"] == 0
    with postgres.connect() as conn:
        for table in ("matches", "external_mappings", "data_sources"):
            assert conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0


def test_postgres_concurrent_imports_serialize(postgres):
    with ThreadPoolExecutor(max_workers=2) as pool:
        reports = list(pool.map(lambda _: load_historical_matches(postgres, [record()]), range(2)))
    assert all(not report["transaction_failures"] for report in reports)
    assert sum(report["matches_inserted"] for report in reports) == 1
    assert sum(report["matches_updated"] for report in reports) == 1
    with postgres.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM matches")).scalar_one() == 1


def test_postgres_dangling_mapping_and_missing_reference(postgres):
    with postgres.begin() as conn:
        source_id = conn.execute(text("INSERT INTO data_sources(name,source_type) VALUES ('fixture','api') RETURNING id")).scalar_one()
        conn.execute(text("INSERT INTO external_mappings(data_source_id,entity_type,entity_id,external_id) VALUES (:id,'match',999999,'one')"), {"id": source_id})
    assert load_historical_matches(postgres, [record()])["transaction_failures"]
    with postgres.begin() as conn:
        conn.execute(text("DELETE FROM seasons"))
    report = load_historical_matches(postgres, [record()])
    assert report["records_deferred"] == 1
