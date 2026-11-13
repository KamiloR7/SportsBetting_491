"""Strict, offline projection of canonical history into chronological ML inputs."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable, Mapping, Any

import pandas as pd

from backend.src.normalizers.match_validation import validate_historical_matches
from app.ml.features.engineer_multisport_features import chronological_split
from app.ml.features.feature_timestamps import validate_feature_cutoff
from app.ml.features.kickoff_safe_features import parse_aware_timestamp
from app.ml.features.prepare_multisport_data import validate_games


@dataclass
class ChronologicalDataset:
    """Validated match partitions; scores are targets/history, never features."""

    train: pd.DataFrame
    test: pd.DataFrame
    sport: str


def _identity(*parts: str) -> str:
    # JSON tuples avoid delimiter collisions in provider identifiers.
    return json.dumps(parts, separators=(",", ":"), ensure_ascii=False)


def build_chronological_dataset(
    records: Iterable[Mapping[str, Any]], sport: str, test_fraction: float = 0.2,
) -> ChronologicalDataset:
    """Fail closed on incomplete history or unverified availability timestamps.

    Input is canonical Sprint 3 history enriched with genuine feature_as_of and
    result_available_at timestamps. Never infer availability from kickoff/date.
    One provider per dataset avoids treating cross-provider copies as games.
    """
    if not isinstance(sport, str):
        raise ValueError("Sport must be NFL, MLB, or EPL")
    sport = sport.upper()
    if sport not in {"NFL", "MLB", "EPL"}:
        raise ValueError(f"Unsupported sport: {sport}; expected NFL, MLB, or EPL")
    rows = list(records)
    if not rows:
        raise ValueError("Historical dataset must not be empty")
    report = validate_historical_matches(rows)
    if report.rejected or report.duplicates:
        raise ValueError(f"Historical integrity failure: {report.counts}")
    projected = []
    for original, game in zip(rows, report.accepted):
        if game["league"] != sport:
            raise ValueError("Dataset must contain only the selected sport")
        if game["status"] != "completed":
            raise ValueError("Only completed matches may enter historical datasets")
        # MLB normalization can infer a year from the date. Dataset provenance
        # requires an explicit source season rather than that fallback.
        if (original.get("season") in (None, "")
                and original.get("source_season") in (None, "")):
            raise ValueError("Missing explicit season provenance")
        if game["season"] is None:
            raise ValueError("Missing season provenance")
        start = parse_aware_timestamp(game["kickoff_utc"], "kickoff_utc")
        as_of = parse_aware_timestamp(original.get("feature_as_of"), "feature_as_of")
        available = parse_aware_timestamp(original.get("result_available_at"), "result_available_at")
        validate_feature_cutoff(start, as_of)
        if available <= start:
            raise ValueError("Result availability must follow kickoff")
        source = game["source"]
        projected.append({
            "game_id": _identity(source, game["game_id"]),
            "source_game_id": game["game_id"], "source": source,
            "season": game["season"], "source_season": game["source_season"],
            "sport": sport,
            # Group on actual UTC kickoff day, not a provider's local date.
            "game_date": start, "start_time": start, "feature_as_of": as_of,
            "result_available_at": available,
            "home_team": _identity(source, sport, game["home_team_id"]),
            "away_team": _identity(source, sport, game["away_team_id"]),
            "home_score": game["home_score"], "away_score": game["away_score"],
        })
    if len({row["source"] for row in projected}) > 1:
        raise ValueError("Use one provider per dataset or resolve cross-provider identities first")
    data = validate_games(sport, pd.DataFrame(projected))
    train, test = chronological_split(data, test_fraction)
    # Every fitted label must have existed before every held-out prediction.
    if train["result_available_at"].max() > test["feature_as_of"].min():
        raise ValueError("Training labels unavailable at the earliest test prediction")
    # Match the existing prior-UTC-day feature history policy. Check every
    # candidate result, including earlier held-out games used for rolling history.
    utc_days = data["game_date"].dt.normalize()
    for game in data.to_dict("records"):
        prior = data[
            (utc_days < game["game_date"].normalize())
            & (data["home_team"].isin([game["home_team"], game["away_team"]])
               | data["away_team"].isin([game["home_team"], game["away_team"]]))
        ]
        validate_feature_cutoff(game["start_time"], game["feature_as_of"], prior["result_available_at"])
    return ChronologicalDataset(train=train, test=test, sport=sport)
