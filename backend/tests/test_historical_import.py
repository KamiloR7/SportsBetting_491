"""Transactional loader unit tests with a rollback-capable fake engine."""
from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace

import pytest

from app.database.historical_import import load_historical_matches, MAX_BATCH_SIZE
from backend.tests.test_match_ingestion import FakeConnection
from backend.tests.test_match_ingestion import FakeResult
from src.normalizers.multi_sport_normalizer import MATCH_FIELDS


def record(league="NFL", **updates):
    row = dict.fromkeys(MATCH_FIELDS)
    row.update(game_id="one", source="fixture", sport={"NFL": "American Football", "MLB": "BASEBALL", "EPL": "SOCCER"}[league],
               league=league, season=2024, week=1, game_date="2024-09-01",
               kickoff_utc="2024-09-01T20:00:00Z", home_team_id="provider-H", away_team_id="provider-A",
               home_team_name="Home", away_team_name="Away", home_team_abbr="H", away_team_abbr="A",
               home_score=3, away_score=1, status="completed", neutral_site=True)
    row.update(updates)
    return row


class FakeEngine:
    def __init__(self):
        self.conn = FakeConnection()
        self.transactions = 0
        self.commit_failure = False

    @contextmanager
    def begin(self):
        self.transactions += 1
        snapshot = deepcopy((self.conn.matches, self.conn.mappings))
        try:
            yield self.conn
            if self.commit_failure:
                raise RuntimeError("forced commit failure")
        except Exception:
            self.conn.matches, self.conn.mappings = snapshot
            raise


def test_insert_reimport_correction_and_kickoff_update():
    engine = FakeEngine()
    first = load_historical_matches(engine, [record(), record()])
    assert first["matches_inserted"] == 1 and first["duplicates_collapsed"] == 1
    second = load_historical_matches(engine, [record(home_score=4, kickoff_utc="2024-09-01T21:00:00Z")])
    assert second["matches_updated"] == 1
    assert len(engine.conn.matches) == len(engine.conn.mappings) == 1
    stored = next(iter(engine.conn.matches.values()))
    assert stored["season_id"] == 7 and stored["neutral_site"] is True
    assert stored["home_score"] == 4 and stored["start_time"] == "2024-09-01T21:00:00Z"
    assert sum("pg_advisory_xact_lock" in sql for sql, _ in engine.conn.calls) == 2


@pytest.mark.parametrize("pattern", ["INSERT INTO external_mappings", "INSERT INTO matches"])
def test_write_failure_rolls_back(pattern):
    engine = FakeEngine()
    engine.conn.fail_sql = pattern
    report = load_historical_matches(engine, [record()])
    assert len(report["transaction_failures"]) == 1
    assert report["matches_inserted"] == report["matches_updated"] == 0
    assert not report["committed"] and not engine.conn.matches and not engine.conn.mappings


def test_later_write_failure_rolls_back_earlier_write():
    engine = FakeEngine()
    original = engine.conn.execute
    def execute(statement, params=None):
        if "INSERT INTO external_mappings" in str(statement) and params["external_id"] == "two":
            raise RuntimeError("second match failed")
        return original(statement, params)
    engine.conn.execute = execute
    report = load_historical_matches(engine, [record(), record(game_id="two")])
    assert report["transaction_failures"] and report["matches_inserted"] == 0
    assert not engine.conn.matches


def test_commit_failure_counts_no_writes():
    engine = FakeEngine()
    engine.commit_failure = True
    report = load_historical_matches(engine, [record()])
    assert report["transaction_failures"] and report["matches_inserted"] == 0
    assert not engine.conn.matches


@pytest.mark.parametrize("pattern,rows", [
    ("SELECT id FROM leagues", []), ("SELECT t.id FROM teams", []),
    ("SELECT id FROM seasons", []), ("SELECT id FROM sports", []),
    ("SELECT t.id FROM teams", [SimpleNamespace(id=10), SimpleNamespace(id=20)]),
    ("SELECT id FROM leagues", [SimpleNamespace(id=1), SimpleNamespace(id=2)]),
    ("SELECT id FROM seasons", [SimpleNamespace(id=7), SimpleNamespace(id=8)]),
])
def test_missing_or_ambiguous_references_deferred(pattern, rows):
    engine = FakeEngine()
    engine.conn.reference_rows[pattern] = rows
    report = load_historical_matches(engine, [record()])
    assert report["records_deferred"] == 1 and report["deferred"][0]["reasons"]
    assert not report["transaction_failures"] and not engine.conn.matches


def test_provider_mapping_resolves_id_only_teams():
    engine = FakeEngine()
    engine.conn.team_mappings = {"provider-H": 10, "provider-A": 20}
    report = load_historical_matches(engine, [record("MLB", home_team_name=None, away_team_name=None, home_team_abbr=None, away_team_abbr=None)])
    assert report["matches_inserted"] == 1


def test_dangling_team_mapping_deferred():
    engine = FakeEngine()
    engine.conn.team_mappings = {"provider-H": 999}
    engine.conn.reference_rows["WHERE t.id = :team_id"] = []
    report = load_historical_matches(engine, [record()])
    assert report["records_deferred"] == 1


def test_dangling_match_mapping_and_identity_change():
    engine = FakeEngine()
    engine.conn.mappings["one"] = 999
    assert load_historical_matches(engine, [record()])["transaction_failures"]
    engine = FakeEngine()
    load_historical_matches(engine, [record()])
    report = load_historical_matches(engine, [record(home_team_name="Different", home_team_abbr="D", home_team_id="other")])
    assert report["transaction_failures"] and report["matches_updated"] == 0


@pytest.mark.parametrize("league,accepted", [("NFL", True), ("EPL", True), ("MLB", False)])
def test_sport_ties(league, accepted):
    report = load_historical_matches(FakeEngine(), [record(league, home_score=1)])
    assert bool(report["matches_inserted"]) == accepted
    assert report["records_rejected"] == (0 if accepted else 1)


@pytest.mark.parametrize("updates", [
    {"kickoff_utc": None}, {"status": "suspended", "league": "MLB", "sport": "BASEBALL"},
    {"status": "incomplete"}, {"status": "scheduled", "home_score": None, "away_score": None},
])
def test_ineligible_data_deferred_without_transaction(updates):
    engine = FakeEngine()
    report = load_historical_matches(engine, [record(**updates)])
    assert report["records_deferred"] == 1
    assert engine.transactions == 0


def test_doubleheaders_and_conflicting_duplicates():
    report = load_historical_matches(FakeEngine(), [record("MLB"), record("MLB", game_id="two")])
    assert report["matches_inserted"] == 2
    report = load_historical_matches(FakeEngine(), [record(), record(home_score=4)])
    assert report["records_rejected"] == 2 and report["matches_inserted"] == 0


def test_batch_limit_and_empty_batch():
    engine = FakeEngine()
    assert load_historical_matches(engine, [])["records_read"] == 0
    with pytest.raises(ValueError, match="limited"):
        load_historical_matches(engine, (record() for _ in range(MAX_BATCH_SIZE + 1)))
    assert engine.transactions == 0


def test_omitted_neutral_site_preserves_existing_value():
    engine = FakeEngine()
    load_historical_matches(engine, [record()])
    result = load_historical_matches(engine, [record(neutral_site=None)])
    assert result["matches_updated"] == 1
    assert next(iter(engine.conn.matches.values()))["neutral_site"] is True


def test_reference_failure_does_not_discard_other_valid_records():
    engine = FakeEngine()
    original = engine.conn.execute
    def execute(statement, params=None):
        if "SELECT t.id FROM teams" in str(statement) and params.get("team_name") == "Missing":
            return FakeResult()
        return original(statement, params)
    engine.conn.execute = execute
    report = load_historical_matches(engine, [record(), record(game_id="two", home_team_name="Missing")])
    assert report["matches_inserted"] == 1 and report["records_deferred"] == 1
    assert report["records_accepted"] == 2


def test_season_identity_change_rolls_back():
    engine = FakeEngine()
    load_historical_matches(engine, [record()])
    engine.conn.reference_rows["SELECT id FROM seasons"] = [SimpleNamespace(id=8)]
    report = load_historical_matches(engine, [record(season=2025)])
    assert report["transaction_failures"]
    assert next(iter(engine.conn.matches.values()))["season_id"] == 7


def test_resolved_same_team_deferred():
    engine = FakeEngine()
    engine.conn.team_mappings = {"provider-H": 10, "provider-A": 10}
    assert load_historical_matches(engine, [record()])["records_deferred"] == 1


def test_low_level_helper_requires_transaction():
    from app.database.match_ingestion import upsert_match
    conn = FakeConnection()
    conn.in_transaction = lambda: False
    with pytest.raises(ValueError, match="active transaction"):
        upsert_match(conn, record())
    assert not conn.calls
