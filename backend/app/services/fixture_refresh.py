"""Opt-in localhost provider polling; never enabled implicitly in tests/deployments."""
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from threading import Event, Lock, Thread
from urllib.request import urlopen
from app.database.refresh_real_matches import FEEDS, normalize, apply_snapshot

logger = logging.getLogger(__name__)


def fetch_current_snapshot(now=None, opener=urlopen):
    now = now or datetime.now(timezone.utc)
    result = {"retrieved_at":now.isoformat(), "source":"ESPN", "matches":[], "sources":[]}
    # UTC yesterday retains US evening games after UTC midnight; tomorrow
    # catches the next fixtures. This is not a bulk history import.
    for league,(feed,_) in FEEDS.items():
        for offset in (-1,0,1):
            day = now.date() + timedelta(days=offset)
            url = f"https://site.api.espn.com/apis/site/v2/sports/{feed}/scoreboard?dates={day:%Y%m%d}&limit=1000"
            with opener(url, timeout=10) as response: raw = response.read()
            payload = json.loads(raw)
            if len(payload.get("events",[])) >= 1000: raise ValueError("Provider response may be truncated")
            result["sources"].append({"url":url,"sha256":hashlib.sha256(raw).hexdigest()})
            result["matches"].extend(normalize(payload,league))
    return result


class FixtureRefreshWorker:
    def __init__(self, engine, interval=120, fetch=fetch_current_snapshot, apply=apply_snapshot):
        if engine.url.host not in {"localhost","127.0.0.1","::1"}:
            raise ValueError("Automatic refresh is limited to a localhost database")
        self.engine, self.fetch, self.apply = engine, fetch, apply
        self.interval = max(60, min(int(interval),3600))
        self.lock, self.stopped = Lock(), Event()
        self.state = {"enabled":True,"source":"ESPN","interval_seconds":self.interval,
                      "state":"starting","last_attempt":None,"last_success":None,
                      "last_error":None,"games_processed":0,"next_refresh":None}
        self.thread = None

    def status(self):
        with self.lock: return dict(self.state)

    def refresh_once(self):
        now = datetime.now(timezone.utc)
        with self.lock: self.state.update(state="refreshing",last_attempt=now.isoformat())
        try:
            snapshot = self.fetch()
            self.apply(snapshot,self.engine)
            with self.lock:
                self.state.update(state="ready",last_success=datetime.now(timezone.utc).isoformat(),
                                  last_error=None,games_processed=len(snapshot["matches"]))
            return True
        except Exception as exc:
            logger.warning("Fixture refresh failed (%s); retained stored data",type(exc).__name__)
            with self.lock: self.state.update(state="error",last_error="Refresh failed. Stored results may be delayed; check the backend log.")
            return False

    def run(self):
        failures = 0
        while not self.stopped.is_set():
            failures = 0 if self.refresh_once() else failures + 1
            delay = self.interval if failures == 0 else min(self.interval * 2 ** min(failures,3),max(self.interval,900))
            with self.lock: self.state["next_refresh"]=(datetime.now(timezone.utc)+timedelta(seconds=delay)).isoformat()
            if self.stopped.wait(delay): break

    def start(self):
        self.thread = Thread(target=self.run,name="local-fixture-refresh",daemon=True)
        self.thread.start()

    def stop(self):
        self.stopped.set()
        if self.thread: self.thread.join(timeout=1)
