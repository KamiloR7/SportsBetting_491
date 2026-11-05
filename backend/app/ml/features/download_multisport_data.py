"""Download public historical results; never used by offline CI tests."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import logging
import os
import tempfile
import time
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd

from app.ml.features.prepare_multisport_data import validate_games

COLUMNS = ["game_id", "game_date", "home_team", "away_team", "home_score", "away_score"]
def source_seasons(as_of: date | None = None) -> dict[str, list[int]]:
    """Return rolling recent seasons, including the current season for each sport."""
    as_of = as_of or date.today()
    nfl_mlb_years = list(range(as_of.year - 3, as_of.year + 1))
    current_epl_start = as_of.year if as_of.month >= 7 else as_of.year - 1
    epl_starts = list(range(current_epl_start - 3, current_epl_start + 1))
    return {"NFL": nfl_mlb_years, "MLB": list(range(as_of.year - 2, as_of.year + 1)),
            "EPL": epl_starts}


def _season_code(start_year: int) -> str:
    return f"{start_year % 100:02d}{(start_year + 1) % 100:02d}"


def build_sources(as_of: date | None = None) -> dict[str, list[str]]:
    """Build feed URLs for a rolling historical window and the current season."""
    seasons = source_seasons(as_of)
    return {
        "NFL": ["https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"],
        "MLB": [f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&season={year}&gameType=R"
                for year in seasons["MLB"]],
        "EPL": [f"https://www.football-data.co.uk/mmz4281/{_season_code(year)}/E0.csv"
                for year in seasons["EPL"]],
    }


SOURCES = build_sources()
logger = logging.getLogger(__name__)
TRANSIENT_HTTP_CODES = {408, 425, 429, 500, 502, 503, 504}


def fetch_source(url: str, *, timeout: int = 60, retries: int = 2,
                 backoff_seconds: float = 1.0, opener=urlopen,
                 sleep=time.sleep) -> bytes:
    """Fetch one public source with bounded retries and sanitized diagnostics."""
    if retries < 0 or timeout <= 0 or backoff_seconds < 0:
        raise ValueError("timeout must be positive; retries and backoff must be nonnegative")
    request = Request(url, headers={"User-Agent": "SportsBetting491-EducationalBaseline/1.0"})
    for attempt in range(retries + 1):
        try:
            with opener(request, timeout=timeout) as response:
                payload = response.read()
            if not payload:
                raise ValueError("Provider returned an empty response")
            return payload
        except HTTPError as exc:
            retryable = exc.code in TRANSIENT_HTTP_CODES
            error_type = f"HTTP {exc.code}"
        except (URLError, TimeoutError) as exc:
            retryable = True
            error_type = type(exc).__name__
        if not retryable or attempt >= retries:
            logger.error("Source request failed (%s) after %d attempt(s); provider URL omitted",
                         error_type, attempt + 1)
            raise RuntimeError(f"Source request failed ({error_type}) after {attempt + 1} attempt(s)") from None
        delay = backoff_seconds * (attempt + 1)
        logger.warning("Transient source request failure (%s); retry %d/%d in %.1f seconds",
                       error_type, attempt + 1, retries, delay)
        sleep(delay)
    raise AssertionError("unreachable")


def _replace_snapshot(output: Path, files: dict[str, bytes]) -> None:
    """Promote a fully validated refresh snapshot, restoring old files on errors."""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix=".refresh-", dir=output.parent))
    backups: dict[Path, Path] = {}
    promoted: list[Path] = []
    try:
        for name, content in files.items():
            (staged / name).write_bytes(content)
        for name in files:
            destination = output / name
            if destination.exists():
                backup = staged / f"backup-{name}"
                os.replace(destination, backup)
                backups[destination] = backup
            os.replace(staged / name, destination)
            promoted.append(destination)
    except Exception:
        for destination in reversed(promoted):
            destination.unlink(missing_ok=True)
        for destination, backup in backups.items():
            if backup.exists():
                os.replace(backup, destination)
        raise
    finally:
        for path in staged.iterdir():
            path.unlink(missing_ok=True)
        staged.rmdir()


def normalize_nfl(payload: bytes, seasons: list[int] | None = None):
    source = pd.read_csv(io.BytesIO(payload))
    seasons = seasons if seasons is not None else source_seasons()["NFL"]
    selected = source[source["season"].isin(seasons) & source["game_type"].eq("REG")]
    completed = selected.dropna(subset=["home_score", "away_score"])
    data = completed.rename(columns={"gameday": "game_date"})[COLUMNS]
    return data, {"source_rows": len(source), "selected_rows": len(selected),
                  "excluded_incomplete": len(selected) - len(completed)}


def normalize_epl(payload: bytes, season: str):
    source = pd.read_csv(io.BytesIO(payload), encoding="utf-8-sig")
    selected = source[source["Div"].eq("E0")].dropna(subset=["FTHG", "FTAG"])
    data = selected.rename(columns={"Date": "game_date", "HomeTeam": "home_team",
                                   "AwayTeam": "away_team", "FTHG": "home_score",
                                   "FTAG": "away_score"}).copy()
    data["game_date"] = pd.to_datetime(data["game_date"], dayfirst=True, errors="raise", utc=True)
    data["game_id"] = [f"EPL-{season}-{date.date()}-{home}-{away}"
                       for date, home, away in zip(data["game_date"], data["home_team"], data["away_team"])]
    return data[COLUMNS], {"source_rows": len(source), "excluded_incomplete_or_other_division": len(source) - len(data)}


def normalize_mlb(payload: bytes):
    games = [game for day in json.loads(payload)["dates"] for game in day["games"]]
    rows = {}
    excluded = Counter()
    for game in games:
        if game.get("gameType") != "R" or game["status"]["detailedState"] not in ("Final", "Game Over", "Completed Early"):
            excluded["not_completed_regular_season"] += 1
            continue
        if any("resum" in key.lower() for key in game):
            excluded["resumed_game_leakage_guard"] += 1
            continue
        home, away = game["teams"]["home"], game["teams"]["away"]
        if home.get("score") is None or away.get("score") is None:
            excluded["missing_score"] += 1
            continue
        row = dict(zip(COLUMNS, [str(game["gamePk"]), game["officialDate"], str(home["team"]["id"]),
                                str(away["team"]["id"]), home["score"], away["score"]]))
        if row["game_id"] in rows:
            if rows[row["game_id"]] != row:
                raise ValueError("Conflicting MLB duplicate")
            excluded["identical_duplicate"] += 1
        rows[row["game_id"]] = row
    return pd.DataFrame(rows.values(), columns=COLUMNS), {"source_rows": len(games), "excluded": dict(excluded)}


def download_datasets(directory: Path, *, retries: int = 2, timeout: int = 60,
                      backoff_seconds: float = 1.0) -> dict:
    """Repeatably refresh all supported datasets; failed refreshes keep old outputs."""
    directory = Path(directory)
    manifest = {"retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "sports": {},
                "usage": "Educational local analysis only. Public access does not grant redistribution rights. Raw provider data is not committed.",
                "date_policy": "Provider match calendar dates; prior-day features exclude all same-day results. Resumed MLB games excluded."}
    outputs: dict[str, bytes] = {}
    for sport, urls in SOURCES.items():
        frames, provenance = [], []
        for index, url in enumerate(urls):
            payload = fetch_source(url, timeout=timeout, retries=retries,
                                   backoff_seconds=backoff_seconds)
            if sport == "NFL":
                data, counts = normalize_nfl(payload)
            elif sport == "MLB":
                data, counts = normalize_mlb(payload)
            else:
                data, counts = normalize_epl(payload, url.split("/")[-2])
            frames.append(data)
            provenance.append({"url": url, "sha256": hashlib.sha256(payload).hexdigest(), **counts})
            outputs[f"{sport.lower()}_source_{index}.bin"] = payload
        clean = validate_games(sport, pd.concat(frames, ignore_index=True))
        path = directory / f"{sport.lower()}_games.csv"
        outputs[path.name] = clean.to_csv(index=False).encode("utf-8")
        manifest["sports"][sport] = {"sources": provenance, "rows": len(clean),
                                    "date_min": clean["game_date"].min().isoformat(),
                                    "date_max": clean["game_date"].max().isoformat()}
        manifest["sports"][sport]["dataset_sha256"] = hashlib.sha256(outputs[path.name]).hexdigest()
    outputs["provenance.json"] = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
    _replace_snapshot(directory, outputs)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/raw"))
    parser.add_argument("--timeout", type=int, default=60, help="Per-request timeout in seconds")
    parser.add_argument("--retries", type=int, default=2, help="Retries for transient source failures")
    parser.add_argument("--backoff-seconds", type=float, default=1.0, help="Linear retry backoff")
    arguments = parser.parse_args()
    try:
        report = download_datasets(arguments.output, retries=arguments.retries,
                                    timeout=arguments.timeout,
                                    backoff_seconds=arguments.backoff_seconds)
    except Exception as exc:
        logger.error("Refresh failed (%s); existing output snapshot was preserved", type(exc).__name__)
        raise SystemExit(1) from None
    print(json.dumps(report, indent=2))
