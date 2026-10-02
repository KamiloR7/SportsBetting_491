"""Download public historical results; never used by offline CI tests."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

from app.ml.features.prepare_multisport_data import validate_games

COLUMNS = ["game_id", "game_date", "home_team", "away_team", "home_score", "away_score"]
SOURCES = {
    "NFL": ["https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"],
    "MLB": ["https://statsapi.mlb.com/api/v1/schedule?sportId=1&season=2024&gameType=R"],
    "EPL": [
        "https://www.football-data.co.uk/mmz4281/2324/E0.csv",
        "https://www.football-data.co.uk/mmz4281/2425/E0.csv",
    ],
}


def normalize_nfl(payload: bytes):
    source = pd.read_csv(io.BytesIO(payload))
    selected = source[source["season"].isin([2023, 2024]) & source["game_type"].eq("REG")]
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


def download_datasets(directory: Path) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    manifest = {"retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "sports": {},
                "usage": "Educational local analysis only. Public access does not grant redistribution rights. Raw provider data is not committed.",
                "date_policy": "Provider match calendar dates; prior-day features exclude all same-day results. Resumed MLB games excluded."}
    for sport, urls in SOURCES.items():
        frames, provenance = [], []
        for index, url in enumerate(urls):
            request = Request(url, headers={"User-Agent": "SportsBetting491-EducationalBaseline/1.0"})
            with urlopen(request, timeout=60) as response:
                payload = response.read()
            (directory / f"{sport.lower()}_source_{index}.bin").write_bytes(payload)
            if sport == "NFL":
                data, counts = normalize_nfl(payload)
            elif sport == "MLB":
                data, counts = normalize_mlb(payload)
            else:
                data, counts = normalize_epl(payload, url.split("/")[-2])
            frames.append(data)
            provenance.append({"url": url, "sha256": hashlib.sha256(payload).hexdigest(), **counts})
        clean = validate_games(sport, pd.concat(frames, ignore_index=True))
        path = directory / f"{sport.lower()}_games.csv"
        clean.to_csv(path, index=False)
        manifest["sports"][sport] = {"sources": provenance, "rows": len(clean),
                                    "date_min": clean["game_date"].min().isoformat(),
                                    "date_max": clean["game_date"].max().isoformat(),
                                    "dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    (directory / "provenance.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/raw"))
    arguments = parser.parse_args()
    print(json.dumps(download_datasets(arguments.output), indent=2))
