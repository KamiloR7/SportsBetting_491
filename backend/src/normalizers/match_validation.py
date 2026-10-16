"""Offline data-quality gate for shared normalized historical match records.

This validates data, not database readiness: date-only records and nonfinal
statuses may be valid here but need an explicit policy in the DATA-25 loader.
No database, network, or ML prediction-label dependency is used.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from .multi_sport_normalizer import (
    MATCH_FIELDS, NormalizationError, canonical_sport, normalize_match_row,
)


@dataclass
class ValidationReport:
    accepted: list[dict[str, Any]] = field(default_factory=list)
    rejected: list[dict[str, Any]] = field(default_factory=list)
    duplicates: list[dict[str, Any]] = field(default_factory=list)
    records_read: int = 0

    @property
    def counts(self) -> dict[str, int]:
        return {"read": self.records_read, "accepted": len(self.accepted),
                "rejected": len(self.rejected), "duplicates": len(self.duplicates)}

    def to_dict(self) -> dict[str, Any]:
        return {"counts": self.counts, "accepted": self.accepted,
                "rejected": self.rejected, "duplicates": self.duplicates}


LEAGUES = {
    "NFL": ("American Football", "NFL"),
    "NATIONAL FOOTBALL LEAGUE": ("American Football", "NFL"),
    "MLB": ("BASEBALL", "MLB"),
    "MAJOR LEAGUE BASEBALL": ("BASEBALL", "MLB"),
    "EPL": ("SOCCER", "EPL"), "PL": ("SOCCER", "EPL"),
    "PREMIER LEAGUE": ("SOCCER", "EPL"),
    "ENGLISH PREMIER LEAGUE": ("SOCCER", "EPL"),
}


def _row_errors(row: Mapping[str, Any]) -> list[str]:
    errors = []
    # Canonical input only; raw provider rows belong in their adapters first.
    for name in ("game_id", "source", "home_team_id", "away_team_id"):
        value = row.get(name)
        if (isinstance(value, bool) or not isinstance(value, (str, int))
                or str(value).strip().lower() in {"", "nan", "none", "null"}):
            errors.append(f"{name}: missing or invalid identifier")
    for name, limit in (("game_id", 160), ("source", 100)):
        if isinstance(row.get(name), str) and len(row[name].strip()) > limit:
            errors.append(f"{name}: exceeds database limit of {limit} characters")
    if not isinstance(row.get("source"), str):
        errors.append("source: expected provider name as text")
    sport, league = row.get("sport"), row.get("league")
    expected = LEAGUES.get(league.strip().upper()) if isinstance(league, str) else None
    if expected is None:
        errors.append("league: expected NFL, MLB or EPL")
    if not isinstance(sport, str) or not sport.strip():
        errors.append("sport: missing or invalid identity")
    elif expected and canonical_sport(sport) != expected[0]:
        errors.append("sport: does not match league")
    if not errors:
        if str(row["home_team_id"]).strip() == str(row["away_team_id"]).strip():
            errors.append("teams: home and away must differ")
        home_name, away_name = row.get("home_team_name"), row.get("away_team_name")
        if isinstance(home_name, str) and isinstance(away_name, str) and home_name.strip() and home_name.strip().casefold() == away_name.strip().casefold():
            errors.append("teams: home and away names must differ")
    return errors


def validate_historical_matches(rows: Iterable[Any]) -> ValidationReport:
    """Normalize canonical rows and report all rejections using zero-based indexes.

    Duplicate key matches PostgreSQL external mappings: (source, game_id).
    Compare full normalized records, including metadata. In a conflicting
    group reject *every* valid occurrence, so input order cannot select a
    winning result. Invalid rows are rejected independently before grouping.
    In a clean identical group retain the first row and count the remainder
    as duplicates. read = accepted + rejected + duplicates.
    """
    report = ValidationReport()
    groups: dict[tuple[str, str], list[tuple[int, dict[str, Any]]]] = {}
    for index, row in enumerate(rows):
        report.records_read += 1
        if not isinstance(row, Mapping):
            report.rejected.append({"index": index, "reasons": ["record: expected a mapping"]})
            continue
        errors = _row_errors(row)
        normalized = None
        if not errors:
            try:
                normalized = normalize_match_row(row)
                if tuple(normalized) != MATCH_FIELDS:
                    errors.append("record: does not match MATCH_FIELDS")
                # NFL normalizer does not use outcome metadata; validate it
                # without adopting the ML helper's binary treatment of ties.
                if normalized["league"] == "NFL" and row.get("outcome") not in (None, ""):
                    expected = None
                    if normalized["status"] == "completed":
                        home, away = normalized["home_score"], normalized["away_score"]
                        expected = "HOME_WIN" if home > away else "AWAY_WIN" if away > home else "TIE"
                    if row["outcome"] != expected:
                        errors.append("outcome: conflicts with NFL scores/status")
            except NormalizationError as exc:
                errors.append(str(exc))
        if errors:
            report.rejected.append({"index": index, "source": row.get("source"),
                                    "game_id": row.get("game_id"), "reasons": errors})
        else:
            key = (normalized["source"], normalized["game_id"])
            groups.setdefault(key, []).append((index, normalized))
    for (source, game_id), group in groups.items():
        first_index, first = group[0]
        if any(record != first for _, record in group[1:]):
            for index, _ in group:
                report.rejected.append({"index": index, "source": source, "game_id": game_id,
                                        "reasons": ["conflicting duplicate source match"]})
        else:
            report.accepted.append(first)
            for index, _ in group[1:]:
                report.duplicates.append({"index": index, "kept_index": first_index,
                                          "source": source, "game_id": game_id})
    report.rejected.sort(key=lambda rejection: rejection["index"])
    report.duplicates.sort(key=lambda duplicate: duplicate["index"])
    return report
