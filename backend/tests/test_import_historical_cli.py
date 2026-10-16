"""Offline DATA-26 CLI tests; no configured application database is used."""
import json
import logging

import pytest

from app.database import import_historical as cli
from backend.tests.test_historical_import import FakeEngine, record


def arguments(tmp_path, rows, sport="NFL"):
    path = tmp_path / "matches.json"
    path.write_text(json.dumps(rows))
    return ["--input", str(path), "--sport", sport, "--format", "json"]


def test_dry_run_no_engine_or_loader(tmp_path, monkeypatch, capsys, caplog):
    args = arguments(tmp_path, [record(), record()])
    def forbidden(*args, **kwargs):
        raise AssertionError("Dry run accessed database")
    monkeypatch.setattr(cli, "create_engine", forbidden)
    monkeypatch.setattr(cli, "load_historical_matches", forbidden)
    with caplog.at_level(logging.INFO):
        assert cli.main(args + ["--dry-run"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["records_read"] == 2 and report["records_accepted"] == 1
    assert report["duplicates_collapsed"] == 1 and report["matches_inserted"] == 0
    assert "Import started" in caplog.text and "Import completed" in caplog.text
    assert "fixture" in caplog.text


@pytest.mark.parametrize("sport", ["NFL", "MLB", "EPL"])
def test_sport_normalization(tmp_path, sport, capsys):
    assert cli.main(arguments(tmp_path, [record(sport)], sport) + ["--dry-run"]) == 0
    assert json.loads(capsys.readouterr().out)["records_accepted"] == 1


def test_conflicting_duplicates(tmp_path, capsys):
    assert cli.main(arguments(tmp_path, [record(), record(home_score=7)]) + ["--dry-run"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["records_rejected"] == 2 and report["records_accepted"] == 0


def test_rejection_and_deferred_reporting(tmp_path, capsys):
    rows = [record(home_score=-1), record(game_id="two", kickoff_utc=None)]
    assert cli.main(arguments(tmp_path, rows) + ["--dry-run"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["records_rejected"] == report["records_deferred"] == 1
    assert report["rejected"][0]["file"].endswith("matches.json")


@pytest.mark.parametrize("content", ["bad JSON", "{}", "[]"])
def test_malformed_file(tmp_path, content):
    path = tmp_path / "bad.json"
    path.write_text(content)
    assert cli.main(["--input", str(path), "--sport", "NFL", "--format", "json", "--dry-run"]) == 2


def test_missing_file(tmp_path):
    assert cli.main(["--input", str(tmp_path / "absent"), "--sport", "NFL", "--format", "json", "--dry-run"]) == 2


def test_missing_database_configuration(tmp_path, monkeypatch):
    monkeypatch.delenv("HISTORICAL_IMPORT_DATABASE_URL", raising=False)
    assert cli.main(arguments(tmp_path, [record()])) == 2


@pytest.mark.parametrize("url", ["sqlite://", "postgresql://user:secret@remote/sportsbetting_import_test", "postgresql://user:secret@localhost/production", "postgresql://user:secret@localhost/sportsbetting_import_test?host=remote"])
def test_unsafe_database_configuration(tmp_path, monkeypatch, url, caplog, capsys):
    monkeypatch.setenv("HISTORICAL_IMPORT_DATABASE_URL", url)
    assert cli.main(arguments(tmp_path, [record()]) + ["--allow-write", "--database-name", "sportsbetting_import_test"]) == 2
    assert "secret" not in caplog.text + capsys.readouterr().out


def test_valid_target_and_loader_invocation(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HISTORICAL_IMPORT_DATABASE_URL", "postgresql://user:secret@localhost/sportsbetting_import_test")
    engine = FakeEngine()
    engine.dispose = lambda: None
    targets = []
    monkeypatch.setattr(cli, "create_engine", lambda url, **kwargs: targets.append(url.database) or engine)
    args = arguments(tmp_path, [record(), record(game_id="two")]) + ["--allow-write", "--database-name", "sportsbetting_import_test", "--batch-size", "1"]
    assert cli.main(args) == 0
    report = json.loads(capsys.readouterr().out)
    assert targets == ["sportsbetting_import_test"]
    assert report["matches_inserted"] == 2 and engine.transactions == 2
    assert cli.main(args) == 0
    assert json.loads(capsys.readouterr().out)["matches_updated"] == 2


def test_transaction_failure_sanitized(tmp_path, monkeypatch, capsys, caplog):
    engine = FakeEngine()
    engine.dispose = lambda: None
    engine.conn.fail_sql = "INSERT INTO matches"
    monkeypatch.setattr(cli, "configured_engine", lambda _: engine)
    assert cli.main(arguments(tmp_path, [record()])) == 3
    report = json.loads(capsys.readouterr().out)
    assert report["matches_inserted"] == 0 and report["transaction_failures"]
    assert "rolled back" in caplog.text


def test_epl_csv_date_only(tmp_path, capsys):
    path = tmp_path / "epl.csv"
    path.write_text("Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR\nE0,11/08/2023,Burnley,Man City,0,3,A\n")
    assert cli.main(["--input", str(path), "--sport", "EPL", "--format", "epl-csv", "--season", "2023-24", "--dry-run"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["records_accepted"] == report["records_deferred"] == 1


def test_mlb_reduced_csv(tmp_path, capsys):
    path = tmp_path / "mlb.csv"
    path.write_text("game_id,game_date,home_team,away_team,home_score,away_score\n1,2024-04-01,119,147,5,3\n")
    assert cli.main(["--input", str(path), "--sport", "MLB", "--format", "mlb-csv", "--season", "2024", "--dry-run"]) == 1
    assert json.loads(capsys.readouterr().out)["records_deferred"] == 1


def test_multiple_files_deduplicated_before_batching(tmp_path, capsys):
    args = arguments(tmp_path, [record()])
    second = tmp_path / "second.json"
    second.write_text(json.dumps([record(home_score=7)]))
    args.insert(2, str(second))
    assert cli.main(args + ["--dry-run"]) == 1
    assert json.loads(capsys.readouterr().out)["records_rejected"] == 2


def test_failed_batch_preserves_prior_commits_and_reports_unattempted(tmp_path, monkeypatch, capsys):
    engine = FakeEngine()
    engine.dispose = lambda: None
    original = engine.conn.execute
    def execute(statement, params=None):
        if "INSERT INTO external_mappings" in str(statement) and params["external_id"] == "two":
            raise RuntimeError("postgresql://user:secret@localhost/db")
        return original(statement, params)
    engine.conn.execute = execute
    monkeypatch.setattr(cli, "configured_engine", lambda _: engine)
    assert cli.main(arguments(tmp_path, [record(), record(game_id="two"), record(game_id="three")]) + ["--batch-size", "1"]) == 3
    output = capsys.readouterr().out
    report = json.loads(output)
    assert report["matches_inserted"] == 1 and report["records_deferred"] == 2
    assert len(engine.conn.matches) == 1
    assert "secret" not in output
    assert "Not attempted" in report["deferred"][1]["reasons"][0]


def test_mlb_schedule_json(tmp_path, capsys):
    path = tmp_path / "schedule.json"
    path.write_text(json.dumps({"dates": [{"games": [{
        "gamePk": 123, "officialDate": "2024-04-01", "gameDate": "2024-04-01T20:00:00Z",
        "gameType": "R", "season": "2024", "status": {"detailedState": "Final"},
        "teams": {"home": {"team": {"id": 1}, "score": 3}, "away": {"team": {"id": 2}, "score": 1}},
    }]}]}))
    assert cli.main(["--input", str(path), "--sport", "MLB", "--format", "mlb-schedule", "--dry-run"]) == 0
    assert json.loads(capsys.readouterr().out)["records_accepted"] == 1


def test_normalized_csv(tmp_path, capsys):
    import csv
    path = tmp_path / "nfl.csv"
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(record()))
        writer.writeheader()
        writer.writerow(record())
    assert cli.main(["--input", str(path), "--sport", "NFL", "--format", "csv", "--dry-run"]) == 0
    assert json.loads(capsys.readouterr().out)["records_accepted"] == 1


@pytest.mark.parametrize("extra", [["--batch-size", "0"], ["--batch-size", "1001"]])
def test_invalid_batch_size(tmp_path, extra):
    assert cli.main(arguments(tmp_path, [record()]) + extra) == 2


def test_malformed_csv_width(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("game_id,source\n1,test,extra\n")
    assert cli.main(["--input", str(path), "--sport", "NFL", "--format", "csv", "--dry-run"]) == 2


@pytest.mark.parametrize("input_format", ["json", "csv"])
@pytest.mark.parametrize("dry_run", [True, False])
@pytest.mark.parametrize("home,away,outcome,accepted", [
    (3, 1, "AWAY_WIN", False),  # Original bypass: home-winning scores.
    (3, 1, "HOME_WIN", True),
    (1, 3, "AWAY_WIN", True),
    (1, 1, "TIE", True),
    (1, 1, "AWAY_WIN", False),
    (3, 1, None, True),
])
def test_nfl_supplied_outcome_uses_data24_in_both_modes(
    tmp_path, monkeypatch, capsys, input_format, dry_run, home, away, outcome, accepted
):
    import csv
    from src.normalizers.match_validation import validate_historical_matches

    row = record(home_score=home, away_score=away, outcome=outcome)
    if outcome is None:
        row.pop("outcome")
    assert bool(validate_historical_matches([row]).accepted) == accepted
    path = tmp_path / f"nfl.{input_format}"
    if input_format == "json":
        path.write_text(json.dumps([row]))
    else:
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(row))
            writer.writeheader()
            writer.writerow(row)
    engine = FakeEngine()
    engine.dispose = lambda: None
    monkeypatch.setattr(cli, "configured_engine", lambda _: engine)
    args = ["--input", str(path), "--sport", "NFL", "--format", input_format]
    if dry_run:
        args.append("--dry-run")
    assert cli.main(args) == (0 if accepted else 1)
    report = json.loads(capsys.readouterr().out)
    assert report["records_rejected"] == (0 if accepted else 1)
    assert report["records_accepted"] == (1 if accepted else 0)
    if not accepted:
        assert "outcome" in report["rejected"][0]["reasons"][0]
    assert engine.transactions == (1 if accepted and not dry_run else 0)


@pytest.mark.parametrize("sport,home,away,outcome,accepted", [
    ("EPL", 1, 1, "DRAW", True), ("EPL", 1, 1, "AWAY_WIN", False),
    ("MLB", 3, 1, "HOME_WIN", True), ("MLB", 3, 1, "AWAY_WIN", False),
    ("MLB", 1, 1, "DRAW", False),
])
def test_other_sport_outcome_regression(tmp_path, capsys, sport, home, away, outcome, accepted):
    args = arguments(tmp_path, [record(sport, home_score=home, away_score=away, outcome=outcome)], sport)
    assert cli.main(args + ["--dry-run"]) == (0 if accepted else 1)
    assert json.loads(capsys.readouterr().out)["records_rejected"] == (0 if accepted else 1)
