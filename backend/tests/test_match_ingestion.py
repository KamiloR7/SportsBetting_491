from types import SimpleNamespace

from backend.app.database.match_ingestion import upsert_match


class FakeResult:
    def __init__(self, row=None, rows=None):
        self.rows = rows if rows is not None else ([] if row is None else [row])

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return self.rows


class FakeConnection:
    """SQL-aware offline fixture; never contacts a database."""
    def __init__(self):
        self.calls = []
        self.existing_match_id = None
        self.matches = {}
        self.mappings = {}
        self.team_ids = {}
        self.team_mappings = {}
        self.reference_rows = {}
        self.fail_sql = None

    def in_transaction(self):
        return True

    def execute(self, statement, params=None):
        sql = " ".join(str(statement).split())
        params = params or {}
        self.calls.append((sql, params))
        if self.fail_sql and self.fail_sql in sql:
            raise RuntimeError("forced database failure")
        for pattern, rows in self.reference_rows.items():
            if pattern in sql:
                return FakeResult(rows=rows)
        if "SELECT id FROM sports" in sql or "SELECT id FROM leagues" in sql:
            return FakeResult(SimpleNamespace(id=1))
        if "SELECT id FROM seasons" in sql:
            return FakeResult(SimpleNamespace(id=7))
        if "SELECT t.id FROM teams" in sql:
            if "team_id" in params:
                return FakeResult(SimpleNamespace(id=params["team_id"]))
            key = params.get("team_name") or params.get("team_abbr")
            if key not in self.team_ids:
                self.team_ids[key] = 10 * (len(self.team_ids) + 1)
            return FakeResult(SimpleNamespace(id=self.team_ids[key]))
        if "SELECT id FROM data_sources" in sql:
            return FakeResult(SimpleNamespace(id=5))
        if "SELECT entity_id FROM external_mappings" in sql:
            if "entity_type = 'team'" in sql:
                target = self.team_mappings.get(params["external_id"])
            else:
                target = self.mappings.get(params["external_id"], self.existing_match_id)
            return FakeResult(SimpleNamespace(entity_id=target)) if target else FakeResult()
        if "SELECT id, league_id" in sql:
            stored = self.matches.get(params["match_id"])
            if stored is None and self.existing_match_id == params["match_id"]:
                stored = dict(id=self.existing_match_id, league_id=1, home_team_id=10, away_team_id=20, season_id=None)
            return FakeResult(SimpleNamespace(**stored)) if stored else FakeResult()
        if "INSERT INTO matches" in sql:
            match_id = 99 + len(self.matches)
            self.matches[match_id] = dict(params, id=match_id)
            return FakeResult(SimpleNamespace(id=match_id))
        if "UPDATE matches" in sql:
            previous = self.matches.get(params["match_id"], {})
            updated = dict(params, id=params["match_id"])
            for field in ("season_id", "neutral_site"):
                if updated[field] is None:
                    updated[field] = previous.get(field)
            self.matches[params["match_id"]] = updated
            return FakeResult(SimpleNamespace(id=params["match_id"]))
        if "INSERT INTO external_mappings" in sql:
            self.mappings[params["external_id"]] = params["entity_id"]
        return FakeResult()


def sample_match():
    return {
        "game_id": "NFL-001",
        "sport": "American Football",
        "league": "NFL",
        "home_team_name": "Kansas City Chiefs",
        "home_team_abbr": "KC",
        "away_team_name": "Buffalo Bills",
        "away_team_abbr": "BUF",
        "kickoff_utc": "2026-10-01T20:00:00+00:00",
        "status": "completed",
        "home_score": 27,
        "away_score": 20,
        "source": "test-source",
    }


def test_new_match_is_inserted():
    conn = FakeConnection()

    match_id = upsert_match(conn, sample_match())

    assert match_id == 99

    sql_calls = [sql for sql, _ in conn.calls]
    assert any("INSERT INTO matches" in sql for sql in sql_calls)
    assert any("INSERT INTO external_mappings" in sql for sql in sql_calls)


def test_existing_match_is_updated():
    conn = FakeConnection()
    conn.existing_match_id = 99

    match_id = upsert_match(conn, sample_match())

    assert match_id == 99

    sql_calls = [sql for sql, _ in conn.calls]
    assert any("UPDATE matches" in sql for sql in sql_calls)
    assert not any("INSERT INTO matches" in sql for sql in sql_calls)


def test_completed_status_maps_to_final():
    conn = FakeConnection()

    upsert_match(conn, sample_match())

    match_insert = next(
        params
        for sql, params in conn.calls
        if "INSERT INTO matches" in sql
    )

    assert match_insert["status"] == "final"

def test_invalid_status_is_rejected():
    conn = FakeConnection()
    match = sample_match()
    match["status"] = "unknown"

    try:
        upsert_match(conn, match)
    except ValueError as exc:
        assert "Unsupported match status" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
