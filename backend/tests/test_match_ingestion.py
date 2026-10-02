from types import SimpleNamespace

from backend.app.database.match_ingestion import upsert_match


class FakeResult:
    def __init__(self, row=None):
        self._row = row

    def first(self):
        return self._row


class FakeConnection:
    def __init__(self):
        self.calls = []
        self.existing_match_id = None

    def execute(self, statement, params=None):
        sql = " ".join(str(statement).split())
        self.calls.append((sql, params))

        if "SELECT id FROM leagues" in sql:
            return FakeResult(SimpleNamespace(id=1))

        if "SELECT t.id FROM teams" in sql:
            team_select_count = sum(
                "SELECT t.id FROM teams" in call[0]
                for call in self.calls
            )
            return FakeResult(
                SimpleNamespace(
                    id=10 if team_select_count == 1 else 20
                )
            )

        if "INSERT INTO data_sources" in sql:
            return FakeResult()

        if "SELECT id FROM data_sources" in sql:
            return FakeResult(SimpleNamespace(id=5))

        if "SELECT entity_id FROM external_mappings" in sql:
            if self.existing_match_id is None:
                return FakeResult(None)

            return FakeResult(
                SimpleNamespace(
                    entity_id=self.existing_match_id
                )
            )

        if "INSERT INTO matches" in sql:
            self.existing_match_id = 99
            return FakeResult(SimpleNamespace(id=99))

        if "UPDATE matches" in sql:
            return FakeResult()

        if "INSERT INTO external_mappings" in sql:
            return FakeResult()

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