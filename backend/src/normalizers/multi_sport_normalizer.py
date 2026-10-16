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
import hashlib
import json
import re
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
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
    "neutral_site",
    # Optional outcome, source-season and timestamp-precision metadata.
    "outcome",
    "source_season",
    "kickoff_precision",
)

SPORT_ALIASES = {
    "NFL": "American Football",
    "AMERICAN FOOTBALL": "American Football",
    "AMERICAN_FOOTBALL": "American Football",
    "FOOTBALL": "American Football",
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
    except (TypeError, ValueError, OverflowError) as exc:
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


def _optional_bool(value: Any) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str) and value in {"True", "False", ""}:
        return {"True": True, "False": False, "": None}[value]
    raise NormalizationError("neutral_site must be a boolean or None")


def normalize_team_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize one team row into TEAM_FIELDS.

    Canonical collector field names are preferred, but a few common aliases are
    accepted to make this layer usable by future MLB/EPL collectors too.
    """
    team_id = _required_text(_first(row, "team_id", "id"), "team_id")
    sport = canonical_sport(_first(row, "sport", "sport_name"))
    league = _required_text(_first(row, "league", "competition"), "league")
    if league.upper() in {"PL", "EPL", "PREMIER LEAGUE", "ENGLISH PREMIER LEAGUE"}:
        league = "EPL"
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
    if "gamePk" in row or str(row.get("league", "")).strip().upper() in {"MLB", "MAJOR LEAGUE BASEBALL"}:
        return normalize_mlb_match(row)
    if "Div" in row or str(_first(row, "league", "competition") or "").strip().upper() in {"PL", "EPL", "PREMIER LEAGUE", "ENGLISH PREMIER LEAGUE"}:
        return normalize_epl_match(row)
    if str(_first(row, "league", "competition") or "").strip().upper() in {"NFL", "NATIONAL FOOTBALL LEAGUE"}:
        return normalize_nfl_match(row)
    return _normalize_match_row(row)


def _normalize_match_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Build the shared record after any sport-specific adaptation."""
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
        "neutral_site": _optional_bool(row.get("neutral_site")),
        "outcome": None,
        "source_season": None,
        "kickoff_precision": None,
    }
    return normalized


def normalize_mlb_match(row: Mapping[str, Any], *, season: Any = None) -> dict[str, Any]:
    """Adapt a Stats API schedule game, reduced ML CSV row or canonical row.

    Reduced CSVs contain provider team IDs (home_team/away_team), not names.
    They are known completed results, but their UTC-midnight game_date is a
    serialized calendar date, never a kickoff. Season defaults to the official
    date's year only when omitted; callers may supply the source query season.
    No new network retrieval or ML filtering policy is introduced here.
    """
    if not isinstance(row, Mapping):
        raise NormalizationError("MLB match must be a mapping")
    raw = "gamePk" in row
    reduced = not raw and "home_team" in row and "away_team" in row
    if row.get("sport") is not None and canonical_sport(row["sport"]) != "BASEBALL":
        raise NormalizationError("MLB match must have sport BASEBALL")
    if row.get("league") is not None and str(row["league"]).upper() not in {"MLB", "MAJOR LEAGUE BASEBALL"}:
        raise NormalizationError("MLB match must have league MLB")

    def identity(value: Any, field: str) -> str:
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            raise NormalizationError(f"Invalid MLB identity: {field}")
        return _required_text(value, field)

    adapted = dict(row, sport="BASEBALL", league="MLB")
    adapted["game_id"] = identity(row.get("gamePk" if raw else "game_id"), "game_id")
    adapted["source"] = identity(row.get("source", "statsapi.mlb.com"), "source")
    day = _required_text(row.get("officialDate" if raw else "game_date"), "game_date")
    try:
        if reduced and len(day) > 10:
            serialized = datetime.fromisoformat(day.replace("Z", "+00:00"))
            if serialized.time() != datetime.min.time() or serialized.utcoffset() not in (None, timezone.utc.utcoffset(None)):
                raise ValueError
            day = serialized.date().isoformat()
        calendar = date.fromisoformat(day)
        if calendar.isoformat() != day:
            raise ValueError
    except ValueError as exc:
        raise NormalizationError(f"Invalid MLB game_date: {day!r}") from exc
    adapted["game_date"] = day
    source_season = _first(row, "source_season", "season")
    if source_season is None:
        source_season = season if season is not None else calendar.year
    year = _int_or_none(source_season, "season")
    if isinstance(source_season, bool) or year is None or not 1876 <= year <= 2100:
        raise NormalizationError("Invalid MLB season")
    if row.get("season") is not None and _int_or_none(row["season"], "season") != year:
        raise NormalizationError("MLB season conflicts with source_season")
    adapted["season"] = year
    timestamp = _text(row.get("gameDate" if raw else "kickoff_utc"))
    kickoff = None
    if timestamp:
        try:
            kickoff = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if kickoff.tzinfo is None or kickoff.utcoffset() is None:
                raise ValueError
            kickoff = kickoff.astimezone(timezone.utc)
        except (ValueError, OverflowError) as exc:
            raise NormalizationError("Invalid MLB kickoff timestamp (timezone required)") from exc
    adapted["kickoff_utc"] = kickoff.isoformat().replace("+00:00", "Z") if kickoff else None
    precision = "timestamp" if kickoff else "date"
    if _text(row.get("kickoff_precision")) not in (None, precision):
        raise NormalizationError("MLB kickoff_precision conflicts with timestamp")
    status_map = {"Final": "completed", "Game Over": "completed", "Completed Early": "completed",
                  "Scheduled": "scheduled", "Pre-Game": "scheduled", "Warmup": "scheduled",
                  "In Progress": "in_progress", "Delayed": "in_progress",
                  "Postponed": "postponed", "Cancelled": "cancelled", "Canceled": "cancelled",
                  "Suspended": "suspended"}
    if raw:
        state = row.get("status")
        status = status_map.get(state.get("detailedState")) if isinstance(state, Mapping) else None
    else:
        status = canonical_status(row["status"]) if _text(row.get("status")) else ("completed" if reduced else None)
    if status not in {"completed", "scheduled", "in_progress", "postponed", "cancelled", "suspended", "incomplete"}:
        raise NormalizationError("Unsupported MLB status")
    adapted["status"] = status
    for side in ("home", "away"):
        entry = row.get("teams", {}).get(side, {}) if raw and isinstance(row.get("teams"), Mapping) else {}
        if not isinstance(entry, Mapping) or not isinstance(entry.get("team", {}), Mapping):
            raise NormalizationError(f"Invalid MLB {side} team")
        team = entry.get("team", {})
        adapted[f"{side}_team_id"] = identity(team.get("id") if raw else row.get(f"{side}_team" if reduced else f"{side}_team_id"), f"{side}_team_id")
        adapted[f"{side}_team_name"] = _text(team.get("name") if raw else row.get(f"{side}_team_name"))
        adapted[f"{side}_team_abbr"] = _text(team.get("abbreviation") if raw else row.get(f"{side}_team_abbr"))
        value = entry.get("score") if raw else row.get(f"{side}_score")
        score = _int_or_none(value, f"{side}_score")
        if isinstance(value, bool) or (score is not None and score < 0):
            raise NormalizationError("MLB scores must be nonnegative integers")
        adapted[f"{side}_score"] = score
    if adapted["home_team_id"] == adapted["away_team_id"]:
        raise NormalizationError("MLB home and away teams must differ")
    if status == "completed" and adapted["home_score"] is not None and adapted["home_score"] == adapted["away_score"]:
        raise NormalizationError("Completed MLB game has tied final scores")
    adapted["game_type"] = row.get("gameType" if raw else "game_type")
    venue = row.get("venue")
    adapted["location"] = _text(venue.get("name")) if isinstance(venue, Mapping) else _text(row.get("location"))
    adapted["neutral_site"] = row.get("neutralSite", row.get("neutral_site"))
    adapted["winner_team_id"] = adapted["winner_team_abbr"] = None
    result = _normalize_match_row(adapted)
    outcome = None
    if status == "completed":
        outcome = "HOME_WIN" if result["home_score"] > result["away_score"] else "AWAY_WIN"
    for field in ("winner_team_id", "winner_team_abbr", "outcome"):
        expected = outcome if field == "outcome" else result[field]
        if _text(row.get(field)) is not None and _text(row[field]) != expected:
            raise NormalizationError(f"MLB {field} conflicts with result/status")
    if raw:
        for side in ("home", "away"):
            declared = row["teams"][side].get("isWinner")
            if declared is not None and (not isinstance(declared, bool) or declared != (result["winner_team_id"] == result[f"{side}_team_id"])):
                raise NormalizationError("MLB isWinner conflicts with result/status")
    result.update(outcome=outcome, source_season=str(source_season), kickoff_precision=precision)
    return result


def normalize_mlb_matches(rows: Iterable[Mapping[str, Any]], *, season: Any = None) -> list[dict[str, Any]]:
    """Normalize schedule game objects or reduced CSV rows without downloads."""
    return _deduplicate([normalize_mlb_match(row, season=season) for row in rows], "game_id")


def normalize_mlb_schedule(payload: Any, *, season: Any = None) -> list[dict[str, Any]]:
    """Read already-downloaded Stats API schedule JSON; perform no retrieval.

    Unlike the ML downloader, this retains nonfinal and resumed games. The
    caller must apply the existing ML exclusion policy before feature use.
    Resume/completion-time metadata has no field in MATCH_FIELDS.
    """
    try:
        if isinstance(payload, (bytes, str)):
            payload = json.loads(payload)
        if not isinstance(payload, Mapping) or not isinstance(payload.get("dates"), list):
            raise ValueError
        games = []
        for day in payload["dates"]:
            if not isinstance(day, Mapping) or not isinstance(day.get("games"), list):
                raise ValueError
            games.extend(day["games"])
    except (ValueError, TypeError, UnicodeDecodeError) as exc:
        raise NormalizationError("Invalid MLB schedule payload: expected dates/games lists") from exc
    return normalize_mlb_matches(games, season=season)


def normalize_epl_match(row: Mapping[str, Any], *, season: Any = None) -> dict[str, Any]:
    """Adapt football-data.org collector rows or football-data.co.uk E0 rows.

    CSV needs season context (argument or Season column). outcome is HOME_WIN,
    DRAW or AWAY_WIN only for completed games. source_season retains the input
    label while season is its starting year. kickoff_precision is timestamp
    or date, according to whether a real clock time is available.
    Its synthetic team
    IDs are provider-scoped names and its match IDs hash season/date/teams;
    these require reference mapping before PostgreSQL loading. CSV Time is
    Europe/London local time. Never invent midnight for a date-only result.
    """
    if not isinstance(row, Mapping):
        raise NormalizationError("EPL match must be a mapping")
    csv_row = "Div" in row
    if csv_row:
        if row["Div"] != "E0":
            raise NormalizationError("EPL CSV must have Div E0")
    else:
        league = _required_text(row.get("league"), "league").upper()
        if league not in {"PL", "EPL", "PREMIER LEAGUE", "ENGLISH PREMIER LEAGUE"}:
            raise NormalizationError("EPL match must identify Premier League")
        if canonical_sport(row.get("sport")) != "SOCCER":
            raise NormalizationError("EPL match must have sport SOCCER")
    source_season = _first(row, "source_season", "Season", "season")
    if source_season is None:
        source_season = season
    label = _required_text(source_season, "source season")
    parse_label = label
    if re.fullmatch(r"\d{4}", label) and 0 <= int(label[:2]) <= 99 and int(label) > 2100:
        parse_label = f"20{label[:2]}-{label[2:]}"  # Provider URL code, e.g. 2324.
    match = re.fullmatch(r"(\d{4})(?:[-/](\d{2}|\d{4}))?", parse_label)
    if not match:
        raise NormalizationError(f"Invalid EPL season: {label!r}")
    start = int(match[1])
    if not 1888 <= start <= 2100 or (match[2] and int(match[2]) != (start + 1 if len(match[2]) == 4 else (start + 1) % 100)):
        raise NormalizationError(f"Invalid EPL season: {label!r}")
    if row.get("source_season") is not None and row.get("season") is not None and _int_or_none(row["season"], "season") != start:
        raise NormalizationError("EPL season conflicts with source_season")
    adapted = dict(row, sport="SOCCER", league="EPL", season=start)

    def identity(value: Any, field: str) -> str:
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            raise NormalizationError(f"Invalid EPL identity: {field}")
        return _required_text(value, field)

    adapted["source"] = identity(row.get("source") or ("football-data.co.uk" if csv_row else None), "source")
    for side, csv_field in (("home", "HomeTeam"), ("away", "AwayTeam")):
        name = identity(row.get(csv_field if csv_row else f"{side}_team_name"), f"{side}_team_name")
        adapted[f"{side}_team_name"] = name
        adapted[f"{side}_team_id"] = identity(row.get(f"{side}_team_id") or (f"football-data.co.uk:team:{name}" if csv_row else None), f"{side}_team_id")
        adapted[f"{side}_team_abbr"] = _text(row.get(f"{side}_team_abbr"))
    if adapted["home_team_id"] == adapted["away_team_id"] or adapted["home_team_name"] == adapted["away_team_name"]:
        raise NormalizationError("EPL home and away teams must differ")
    day = _text(row.get("Date" if csv_row else "game_date"))
    calendar_date = None
    if day:
        try:
            if csv_row:
                fmt = "%d/%m/%Y" if len(day.split("/")[-1]) == 4 else "%d/%m/%y"
                calendar_date = datetime.strptime(day, fmt).date()
            else:
                calendar_date = date.fromisoformat(day)
                if calendar_date.isoformat() != day:
                    raise ValueError
        except ValueError as exc:
            raise NormalizationError(f"Invalid EPL match date: {day!r}") from exc
    timestamp = _text(row.get("kickoff_utc"))
    kickoff = None
    try:
        if timestamp:
            kickoff = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if kickoff.tzinfo is None or kickoff.utcoffset() is None:
                raise ValueError
            kickoff = kickoff.astimezone(timezone.utc)
        if csv_row and _text(row.get("Time")):
            if calendar_date is None:
                raise ValueError
            local = datetime.strptime(f"{calendar_date} {row['Time']}", "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("Europe/London"))
            converted = local.astimezone(timezone.utc)
            if converted.astimezone(local.tzinfo).replace(tzinfo=None) != local.replace(tzinfo=None):
                raise ValueError
            if kickoff is not None and kickoff != converted:
                raise ValueError
            kickoff = converted
    except (ValueError, OverflowError) as exc:
        raise NormalizationError("Invalid EPL kickoff timestamp/time (timezone required)") from exc
    if calendar_date is None:
        if kickoff is None:
            raise NormalizationError("EPL match requires a valid date")
        calendar_date = kickoff.date()
    elif kickoff is not None:
        # The .org collector defines game_date in Eastern time; CSV uses UK time.
        zone = "Europe/London" if csv_row or adapted["source"] == "football-data.co.uk" else "America/New_York"
        if kickoff.astimezone(ZoneInfo(zone)).date() != calendar_date:
            raise NormalizationError("EPL kickoff conflicts with source match date")
    adapted["game_date"] = calendar_date.isoformat()
    adapted["kickoff_utc"] = kickoff.isoformat().replace("+00:00", "Z") if kickoff else None
    precision = "timestamp" if kickoff else "date"
    if _text(row.get("kickoff_precision")) not in {None, precision}:
        raise NormalizationError("EPL kickoff_precision conflicts with timestamp")
    if csv_row:
        fields = [str(start), adapted["game_date"], adapted["home_team_name"], adapted["away_team_name"]]
        synthetic = "EPL-" + hashlib.sha256(json.dumps(fields).encode()).hexdigest()
        adapted["game_id"] = identity(_first(row, "game_id", "match_id") or synthetic, "game_id")
    else:
        adapted["game_id"] = identity(row.get("game_id"), "game_id")
    for side, field in (("home", "FTHG"), ("away", "FTAG")):
        value = row.get(field if csv_row else f"{side}_score")
        score = _int_or_none(value, field)
        if isinstance(value, bool) or (score is not None and score < 0):
            raise NormalizationError("EPL scores must be nonnegative integers")
        adapted[f"{side}_score"] = score
    status = canonical_status(row["status"]) if _text(row.get("status")) else ("completed" if csv_row else None)
    if status not in {"completed", "scheduled", "in_progress", "postponed", "cancelled", "suspended", "incomplete"}:
        raise NormalizationError(f"Unsupported EPL status: {status}")
    adapted["status"] = status
    adapted["winner_team_id"] = adapted["winner_team_abbr"] = None
    adapted["location"] = _first(row, "location", "venue", "Venue")
    result = _normalize_match_row(adapted)
    outcome = None
    if status == "completed":
        home, away = result["home_score"], result["away_score"]
        outcome = "HOME_WIN" if home > away else "AWAY_WIN" if away > home else "DRAW"
        if outcome == "DRAW":
            result["winner_team_abbr"] = "DRAW"
    for field in ("winner_team_id", "winner_team_abbr", "outcome"):
        supplied = _text(row.get(field))
        expected = outcome if field == "outcome" else result[field]
        if field == "winner_team_abbr" and supplied == "TIE" and outcome == "DRAW":
            supplied = "DRAW"  # Existing soccer collector terminology.
        if supplied is not None and supplied != expected:
            raise NormalizationError(f"EPL {field} conflicts with final result/status")
    if _text(row.get("FTR")) and {"H": "HOME_WIN", "D": "DRAW", "A": "AWAY_WIN"}.get(row["FTR"]) != outcome:
        raise NormalizationError("EPL FTR conflicts with final scores")
    result.update(outcome=outcome, source_season=label, kickoff_precision=precision)
    return result


def normalize_epl_matches(rows: Iterable[Mapping[str, Any]], *, season: Any = None) -> list[dict[str, Any]]:
    """Normalize a season's records, collapsing identical source matches."""
    return _deduplicate([normalize_epl_match(row, season=season) for row in rows], "game_id")


def normalize_nfl_match(row: Mapping[str, Any]) -> dict[str, Any]:
    """Validate collector/canonical NFL rows; retain source IDs, not DB IDs.

    game_date retains the source calendar date. A missing source clock time
    combined with the collector's synthetic Eastern midnight is date-only:
    kickoff_utc becomes None, so it cannot be mistaken for an actual kickoff.
    Explicit aware timestamps otherwise retain their instant in UTC. No time
    is fabricated for date-only rows. Seasons use the NFL season year.
    """
    if not isinstance(row, Mapping):
        raise NormalizationError("NFL match must be a mapping")
    adapted = dict(row)
    if canonical_sport(_first(row, "sport", "sport_name")) != "American Football":
        raise NormalizationError("NFL match must have an American Football sport identity")
    if str(_first(row, "league", "competition") or "").strip().upper() not in {"NFL", "NATIONAL FOOTBALL LEAGUE"}:
        raise NormalizationError("NFL match must have league NFL")
    for field in ("game_id", "source", "home_team_id", "away_team_id", "home_team_abbr", "away_team_abbr"):
        value = row.get(field)
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            raise NormalizationError(f"Invalid NFL identity: {field}")
        adapted[field] = _required_text(value, field)
    if adapted["home_team_id"] == adapted["away_team_id"] or adapted["home_team_abbr"] == adapted["away_team_abbr"]:
        raise NormalizationError("NFL home and away teams must differ")
    for field in ("season", "week"):
        number = _int_or_none(row.get(field), field)
        if number is None or number < 1 or (field == "season" and not 1920 <= number <= 2100):
            raise NormalizationError(f"Invalid NFL {field}")
        adapted[field] = number
    date_text = _required_text(row.get("game_date"), "game_date")
    try:
        calendar_date = date.fromisoformat(date_text)
        if calendar_date.isoformat() != date_text:
            raise ValueError
    except ValueError as exc:
        raise NormalizationError(f"Invalid NFL game_date: {date_text!r}") from exc
    clock = _text(row.get("game_time_eastern"))
    eastern = ZoneInfo("America/New_York")
    local = None
    if clock:
        try:
            local = datetime.strptime(f"{date_text} {clock}", "%Y-%m-%d %H:%M").replace(tzinfo=eastern)
        except ValueError as exc:
            raise NormalizationError(f"Invalid NFL game_time_eastern: {clock!r}") from exc
    timestamp = _text(row.get("kickoff_utc"))
    kickoff = None
    if timestamp:
        try:
            kickoff = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if kickoff.tzinfo is None or kickoff.utcoffset() is None:
                raise ValueError
            kickoff = kickoff.astimezone(timezone.utc)
        except (ValueError, OverflowError) as exc:
            raise NormalizationError(f"Invalid NFL kickoff_utc (timezone required): {timestamp!r}") from exc
        if local is not None and kickoff != local.astimezone(timezone.utc):
            raise NormalizationError("NFL kickoff_utc conflicts with source date/time")
        if kickoff.astimezone(eastern).date() != calendar_date:
            raise NormalizationError("NFL kickoff_utc conflicts with source game_date")
        if local is None and adapted["source"] == "nflverse/nflreadpy":
            inferred = datetime.combine(calendar_date, datetime.min.time(), tzinfo=eastern)
            if kickoff == inferred.astimezone(timezone.utc):
                kickoff = None
    elif local is not None:
        kickoff = local.astimezone(timezone.utc)
    adapted["kickoff_utc"] = kickoff.isoformat().replace("+00:00", "Z") if kickoff else None
    adapted["sport"], adapted["league"] = "American Football", "NFL"
    status = canonical_status(row.get("status"))
    if status not in {"scheduled", "in_progress", "completed", "postponed", "cancelled", "incomplete"}:
        raise NormalizationError(f"Unsupported NFL status: {status}")
    adapted["status"] = status
    for side in ("home", "away"):
        field = f"{side}_score"
        score = _int_or_none(row.get(field), field)
        if isinstance(row.get(field), bool) or (score is not None and score < 0):
            raise NormalizationError(f"NFL {field} must be a nonnegative integer")
        adapted[field] = score
    # Derive from scores, then validate supplied winner metadata against it.
    adapted["winner_team_id"] = adapted["winner_team_abbr"] = None
    result = _normalize_match_row(adapted)
    for field in ("winner_team_id", "winner_team_abbr"):
        supplied = _text(row.get(field))
        if supplied is not None and supplied != result[field]:
            raise NormalizationError(f"NFL {field} conflicts with final result/status")
    return result


def normalize_nfl_matches(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate by provider and external match ID; reject conflicts."""
    return _deduplicate([normalize_nfl_match(row) for row in rows], "game_id")





def _entity_key(row: Mapping[str, Any], id_field: str) -> tuple[str, str, str]:
    return (str(row["sport"]), str(row["league"]), str(row[id_field]))


def _deduplicate(rows: Sequence[dict[str, Any]], id_field: str) -> list[dict[str, Any]]:
    """Remove exact duplicates and reject conflicting rows with the same scoped ID."""
    output: list[dict[str, Any]] = []
    seen: dict[tuple[str, ...], dict[str, Any]] = {}

    for row in rows:
        key = _entity_key(row, id_field)
        if id_field == "game_id" and row["league"] in {"NFL", "EPL", "MLB"}:
            key += (str(row["source"]),)
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

    match_keys = {
        _entity_key(row, "game_id") + ((str(row["source"]),) if row["league"] in {"NFL", "EPL", "MLB"} else ())
        for row in matches
    }
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
