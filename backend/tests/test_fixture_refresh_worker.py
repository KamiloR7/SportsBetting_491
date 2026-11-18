import io
import json
from datetime import datetime, timezone
from types import SimpleNamespace
import pytest
from app.services.fixture_refresh import FixtureRefreshWorker, fetch_current_snapshot
from app.database.refresh_real_matches import normalize
from tests.test_real_fixture_refresh import event


def test_current_fetch_keeps_previous_utc_day_and_all_sports():
    requests=[]
    def opener(url,timeout):
        requests.append((url,timeout))
        return io.BytesIO(json.dumps({"events":[]}).encode())
    result=fetch_current_snapshot(datetime(2026,11,16,1,tzinfo=timezone.utc),opener)
    assert len(requests)==9
    assert all(timeout==10 for _,timeout in requests)
    assert {url.split("dates=")[1][:8] for url,_ in requests}=={"20261115","20261116","20261117"}
    assert len(result["sources"])==9 and result["matches"]==[]


def test_worker_reports_failure_without_claiming_a_new_success():
    applied=[]
    worker=FixtureRefreshWorker(SimpleNamespace(url=SimpleNamespace(host="127.0.0.1")),120,
        fetch=lambda:{"matches":[{"status":"completed"}]},apply=lambda snapshot,engine:applied.append(snapshot))
    assert worker.refresh_once() is True
    first=worker.status()
    assert first["state"]=="ready" and first["games_processed"]==1 and first["last_success"]
    def fail():raise OSError("upstream unavailable")
    worker.fetch=fail
    assert worker.refresh_once() is False
    current=worker.status()
    assert current["state"]=="error" and current["last_success"]==first["last_success"]
    assert current["last_error"] and len(applied)==1
    current["state"]="changed"
    assert worker.status()["state"]=="error"


def test_worker_local_only_and_minimum_poll_interval():
    with pytest.raises(ValueError,match="localhost"):
        FixtureRefreshWorker(SimpleNamespace(url=SimpleNamespace(host="example.com")))
    worker=FixtureRefreshWorker(SimpleNamespace(url=SimpleNamespace(host="localhost")),1)
    assert worker.interval==60


def test_in_progress_scores_are_snapshots_without_being_final():
    row=normalize(event("in",False),"NFL")[0]
    assert (row["home_score"],row["away_score"],row["status"])==(2,1,"in_progress")
    data=event("post",True)
    del data["events"][0]["competitions"][0]["competitors"][0]["score"]
    with pytest.raises(ValueError,match="both final scores"):normalize(data,"NFL")


def test_failed_cycle_backs_off_and_can_stop_without_sleeping():
    worker=FixtureRefreshWorker(SimpleNamespace(url=SimpleNamespace(host="localhost")),120,
        fetch=lambda:(_ for _ in ()).throw(OSError("offline")))
    class StopAfterOne:
        def is_set(self):return False
        def wait(self,delay):self.delay=delay;return True
    stopped=StopAfterOne();worker.stopped=stopped
    worker.run()
    assert stopped.delay==240
    assert worker.status()["next_refresh"] is not None
