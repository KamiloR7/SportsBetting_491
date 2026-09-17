"""Normalize team and match data from multiple sports into one shared schema.

This module is intentionally source-agnostic. Collectors are responsible for
retrieving source data; this module makes the resulting team and match rows
consistent before they are used by analytics, feature engineering, or models.

Example:
    python -m src.normalizers.multi_sport_normalizer \
        --teams data/development/nfl_teams.csv data/development/uefa_cl_teams.csv \
        --matches data/development/nfl_games_2026.csv data/development/uefa_cl_games_2026.csv \
        --output-dir data/normalized
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


TEAM_FIELDS = (
    "team_id",
    "sport",
    "league",
    "team_abbr",
    "team_name",
    "conference",
    "division",
    "country",
    "venue",
    "founded",
    "source",
)

MATCH_FIELDS = (
    "game_id",
    "sport",
    "league",
    "season",
    "week",
    "game_type",
    "game_date",
    "game_time_eastern",
    "kickoff_utc",
    "home_team_id",
    "home_team_abbr",
    "home_team_name",
    "away_team_id",
    "away_team_abbr",
    "away_team_name",
    "home_score",
    "away_score",
    "status",
    "winner_team_id",
    "winner_team_abbr",
    "location",
    "source",
)

SPORT_ALIASES = {
    "NFL": "FOOTBALL",
    "AMERICAN FOOTBALL": "FOOTBALL",
    "AMERICAN_FOOTBALL": "FOOTBALL",
    "FOOTBALL": "FOOTBALL",
    "UEFA": "SOCCER",
    "EPL": "SOCCER",
    "SOCCER": "SOCCER",
    "ASSOCIATION FOOTBALL": "SOCCER",
    "MLB": "BASEBALL",
    "BASEBALL": "BASEBALL",
}

STATUS_ALIASES = {
    "FINAL": "completed",
    "FINISHED": "completed",
    "COMPLETED": "completed",
    "CLOSED": "completed",
    "AWARDED": "completed",
    "SCHEDULED": "scheduled",
    "TIMED": "scheduled",
    "PRE": "scheduled",
    "NOT_STARTED": "scheduled",
    "IN_PROGRESS": "in_progress",
    "IN PLAY": "in_progress",
    "IN_PLAY": "in_progress",
    "LIVE": "in_progress",
    "PAUSED": "in_progress",
    "POSTPONED": "postponed",
    "SUSPENDED": "suspended",
    "CANCELLED": "cancelled",
    "CANCELED": "cancelled",
    "INCOMPLETE": "incomplete",
}


class NormalizationError(ValueError):
    """Raised when a row cannot be normalized into the shared schema."""


def _first(row: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _int_or_none(value: Any, field: str) -> int | None:
    if value in (None, ""):
        return None
    try:
        # Handles values read from CSV such as "2026" and "2026.0".
        number = float(str(value).strip())
        if not number.is_integer():
            raise ValueError
        return int(number)
    except (TypeError, ValueError) as exc:
        raise NormalizationError(f"{field} must be an integer-compatible value: {value!r}") from exc


def _required_text(value: Any, field: str) -> str:
    text = _text(value)
    if text is None:
        raise NormalizationError(f"Missing required field: {field}")
    return text


def canonical_sport(value: Any) -> str:
    sport = _required_text(value, "sport").upper().replace("-", " ")
    return SPORT_ALIASES.get(sport, sport.replace(" ", "_"))


def canonical_status(value: Any) -> str:
    status = _required_text(value, "status")
    key = status.upper().replace("-", "_")
    return STATUS_ALIASES.get(key, status.lower().replace(" ", "_"))


def normalize_team_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize one team row into TEAM_FIELDS.

    Canonical collector field names are preferred, but a few common aliases are
    accepted to make this layer usable by future MLB/EPL collectors too.
    """
    team_id = _required_text(_first(row, "team_id", "id"), "team_id")
    sport = canonical_sport(_first(row, "sport", "sport_name"))
    league = _required_text(_first(row, "league", "competition"), "league")
    team_name = _required_text(_first(row, "team_name", "name", "display_name"), "team_name")
    team_abbr = _required_text(
        _first(row, "team_abbr", "abbreviation", "abbr", "tla", "short_name", "shortName")
        or team_id,
        "team_abbr",
    ).upper()

    normalized = {
        "team_id": team_id,
        "sport": sport,
        "league": league,
        "team_abbr": team_abbr,
        "team_name": team_name,
        "conference": _text(_first(row, "conference", "area")),
        "division": _text(_first(row, "division")),
        "country": _text(_first(row, "country")),
        "venue": _text(_first(row, "venue", "stadium")),
        "founded": _int_or_none(_first(row, "founded", "founded_year"), "founded"),
        "source": _text(_first(row, "source", "data_source")),
    }
    return normalized


def normalize_match_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize one game/match row into MATCH_FIELDS."""
    game_id = _required_text(_first(row, "game_id", "match_id", "id"), "game_id")
    sport = canonical_sport(_first(row, "sport", "sport_name"))
    league = _required_text(_first(row, "league", "competition"), "league")
    home_team_id = _required_text(_first(row, "home_team_id", "home_id"), "home_team_id")
    away_team_id = _required_text(_first(row, "away_team_id", "away_id"), "away_team_id")
    status = canonical_status(_first(row, "status", "game_status"))

    home_score = _int_or_none(_first(row, "home_score", "score_home"), "home_score")
    away_score = _int_or_none(_first(row, "away_score", "score_away"), "away_score")

    if status == "completed" and (home_score is None or away_score is None):
        raise NormalizationError(f"Completed game {game_id} is missing a final score")

    winner_id = _text(_first(row, "winner_team_id", "winner_id"))
    winner_abbr = _text(_first(row, "winner_team_abbr", "winner_abbr"))

    # Derive a winner only when the game is final and both scores are present.
    if status == "completed" and home_score is not None and away_score is not None:
        if home_score > away_score:
            winner_id = winner_id or home_team_id
            winner_abbr = winner_abbr or _text(_first(row, "home_team_abbr", "home_abbr"))
        elif away_score > home_score:
            winner_id = winner_id or away_team_id
            winner_abbr = winner_abbr or _text(_first(row, "away_team_abbr", "away_abbr"))
        else:
            winner_id = None
            winner_abbr = winner_abbr or "TIE"

    normalized = {
        "game_id": game_id,
        "sport": sport,
        "league": league,
        "season": _int_or_none(_first(row, "season", "season_year", "year"), "season"),
        "week": _int_or_none(_first(row, "week", "matchday", "round"), "week"),
        "game_type": _text(_first(row, "game_type", "stage", "season_type")),
        "game_date": _text(_first(row, "game_date", "date")),
        "game_time_eastern": _text(_first(row, "game_time_eastern", "time_eastern")),
        "kickoff_utc": _text(_first(row, "kickoff_utc", "start_time_utc", "utc_date", "utcDate")),
        "home_team_id": home_team_id,
        "home_team_abbr": _text(_first(row, "home_team_abbr", "home_abbr")),
        "home_team_name": _text(_first(row, "home_team_name", "home_name")),
        "away_team_id": away_team_id,
        "away_team_abbr": _text(_first(row, "away_team_abbr", "away_abbr")),
        "away_team_name": _text(_first(row, "away_team_name", "away_name")),
        "home_score": home_score,
        "away_score": away_score,
        "status": status,
        "winner_team_id": winner_id,
        "winner_team_abbr": winner_abbr,
        "location": _text(_first(row, "location", "venue", "stadium")),
        "source": _text(_first(row, "source", "data_source")),
    }
    return normalized


def _entity_key(row: Mapping[str, Any], id_field: str) -> tuple[str, str, str]:
    return (str(row["sport"]), str(row["league"]), str(row[id_field]))


def _deduplicate(rows: Sequence[dict[str, Any]], id_field: str) -> list[dict[str, Any]]:
    """Remove exact duplicates and reject conflicting rows with the same scoped ID."""
    output: list[dict[str, Any]] = []
    seen: dict[tuple[str, str, str], dict[str, Any]] = {}

    for row in rows:
        key = _entity_key(row, id_field)
        previous = seen.get(key)
        if previous is None:
            seen[key] = row
            output.append(row)
            continue
        if previous != row:
            raise NormalizationError(f"Conflicting duplicate {id_field} for {key}")

    return output


def normalize_teams(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized = [normalize_team_row(row) for row in rows]
    return _deduplicate(normalized, "team_id")


def normalize_matches(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized = [normalize_match_row(row) for row in rows]
    return _deduplicate(normalized, "game_id")


def validate_cross_references(
    teams: Sequence[Mapping[str, Any]],
    matches: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Validate IDs, schemas, and match-to-team references across all sports."""
    checks: list[str] = []

    for index, row in enumerate(teams):
        if tuple(row.keys()) != TEAM_FIELDS:
            raise NormalizationError(f"Team row {index} does not match the canonical team schema")

    for index, row in enumerate(matches):
        if tuple(row.keys()) != MATCH_FIELDS:
            raise NormalizationError(f"Match row {index} does not match the canonical match schema")

    team_keys = {_entity_key(row, "team_id") for row in teams}
    if len(team_keys) != len(teams):
        raise NormalizationError("Duplicate normalized team keys detected")

    match_keys = {_entity_key(row, "game_id") for row in matches}
    if len(match_keys) != len(matches):
        raise NormalizationError("Duplicate normalized match keys detected")

    for index, match in enumerate(matches):
        home_key = (str(match["sport"]), str(match["league"]), str(match["home_team_id"]))
        away_key = (str(match["sport"]), str(match["league"]), str(match["away_team_id"]))
        if home_key not in team_keys:
            raise NormalizationError(f"Match row {index} references unknown home team {home_key}")
        if away_key not in team_keys:
            raise NormalizationError(f"Match row {index} references unknown away team {away_key}")
        if home_key == away_key:
            raise NormalizationError(f"Match row {index} has the same home and away team")

    checks.append(f"PASS: {len(teams)} teams match the canonical schema")
    checks.append(f"PASS: {len(matches)} matches match the canonical schema")
    checks.append("PASS: normalized team keys are unique within sport and league")
    checks.append("PASS: normalized match keys are unique within sport and league")
    checks.append("PASS: every match references known normalized teams")
    return checks


def read_csv(path: str | Path) -> list[dict[str, str]]:
    input_path = Path(path)
    if not input_path.exists():
        raise NormalizationError(f"Input file does not exist: {input_path}")
    with input_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise NormalizationError(f"Input file is empty: {input_path}")
    return rows


def write_csv(rows: Sequence[Mapping[str, Any]], path: str | Path, fieldnames: Sequence[str]) -> Path:
    if not rows:
        raise NormalizationError("Cannot write an empty normalized dataset")
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def normalize_files(
    team_paths: Sequence[str | Path],
    match_paths: Sequence[str | Path],
    output_dir: str | Path,
) -> tuple[Path, Path, list[str]]:
    team_rows = [row for path in team_paths for row in read_csv(path)]
    match_rows = [row for path in match_paths for row in read_csv(path)]

    teams = normalize_teams(team_rows)
    matches = normalize_matches(match_rows)
    checks = validate_cross_references(teams, matches)

    output = Path(output_dir)
    teams_path = write_csv(teams, output / "teams.csv", TEAM_FIELDS)
    matches_path = write_csv(matches, output / "matches.csv", MATCH_FIELDS)
    return teams_path, matches_path, checks


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize multi-sport team and match CSV data")
    parser.add_argument("--teams", nargs="+", required=True, help="One or more team CSV files")
    parser.add_argument("--matches", nargs="+", required=True, help="One or more match/game CSV files")
    parser.add_argument("--output-dir", default="data/normalized", help="Output directory")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        teams_path, matches_path, checks = normalize_files(
            args.teams,
            args.matches,
            args.output_dir,
        )
    except NormalizationError as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"Normalized teams -> {teams_path}")
    print(f"Normalized matches -> {matches_path}")
    for check in checks:
        print(check)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
