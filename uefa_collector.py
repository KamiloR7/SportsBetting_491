"""UEFA team and match collector for the multi-sport prediction project.

Primary prototype source: football-data.org API v4.

The collector keeps source retrieval separate from normalization so the same
multi-sport schema used by the NFL collector can also be used for UEFA data.
The default competition is the UEFA Champions League (``CL``), but another
football-data.org UEFA competition code can be supplied when needed.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

SOURCE_NAME = "football-data.org/v4"
SPORT = "SOCCER"
DEFAULT_COMPETITION_CODE = "CL"
DEFAULT_LEAGUE_NAME = "UEFA Champions League"
BASE_URL = "https://api.football-data.org/v4"
EASTERN = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")


class UEFACollectorError(RuntimeError):
    """Raised when UEFA source data cannot be loaded or normalized."""


@dataclass(frozen=True)
class CollectorResult:
    teams: list[dict[str, Any]]
    games: list[dict[str, Any]]


def _safe_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise UEFACollectorError(f"Expected integer-compatible value, got {value!r}") from exc


def _parse_utc_datetime(value: Any) -> datetime | None:
    if not value:
        return None

    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise UEFACollectorError(f"Could not parse UTC kickoff time: {value!r}") from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _kickoff_fields(value: Any) -> tuple[str | None, str | None, str | None]:
    """Return game_date, Eastern game time, and canonical UTC ISO timestamp."""
    parsed = _parse_utc_datetime(value)
    if parsed is None:
        return None, None, None

    eastern = parsed.astimezone(EASTERN)
    return eastern.date().isoformat(), eastern.strftime("%H:%M"), parsed.isoformat()


def _status(value: Any, home_score: int | None, away_score: int | None) -> str:
    source_status = str(value or "").upper()

    if source_status in {"FINISHED", "AWARDED"}:
        return "completed" if home_score is not None and away_score is not None else "incomplete"
    if source_status in {"IN_PLAY", "PAUSED", "EXTRA_TIME", "PENALTY_SHOOTOUT"}:
        return "in_progress"
    if source_status in {"SCHEDULED", "TIMED"}:
        return "scheduled"
    if source_status in {"POSTPONED", "SUSPENDED", "CANCELLED"}:
        return source_status.lower()

    if home_score is not None and away_score is not None:
        return "completed"
    return "scheduled"


def _winner_side(home_score: int | None, away_score: int | None) -> str | None:
    if home_score is None or away_score is None:
        return None
    if home_score > away_score:
        return "home"
    if away_score > home_score:
        return "away"
    return "tie"


def _team_abbr(team: Mapping[str, Any]) -> str:
    value = team.get("tla") or team.get("shortName") or team.get("id")
    if value in (None, ""):
        raise UEFACollectorError("Team row is missing an id/TLA")
    return str(value)


def normalize_team(
    row: Mapping[str, Any],
    league_name: str = DEFAULT_LEAGUE_NAME,
) -> dict[str, Any]:
    """Map one football-data.org team row into the shared team shape."""
    team_id = row.get("id")
    team_name = row.get("name")
    if team_id in (None, "") or not team_name:
        raise UEFACollectorError("Team row is missing id or name")

    area = row.get("area") if isinstance(row.get("area"), Mapping) else {}

    return {
        "team_id": str(team_id),
        "sport": SPORT,
        "league": league_name,
        "team_abbr": _team_abbr(row),
        "team_name": str(team_name),
        "conference": area.get("name"),
        "division": None,
        "country": area.get("name"),
        "venue": row.get("venue"),
        "founded": _safe_int(row.get("founded")),
        "source": SOURCE_NAME,
    }


def normalize_game(
    row: Mapping[str, Any],
    teams_by_id: Mapping[str, Mapping[str, Any]],
    league_name: str = DEFAULT_LEAGUE_NAME,
) -> dict[str, Any]:
    """Map one football-data.org match row into the shared match shape."""
    game_id = row.get("id")
    home = row.get("homeTeam") if isinstance(row.get("homeTeam"), Mapping) else {}
    away = row.get("awayTeam") if isinstance(row.get("awayTeam"), Mapping) else {}
    home_id_raw = home.get("id")
    away_id_raw = away.get("id")

    if game_id in (None, "") or home_id_raw in (None, "") or away_id_raw in (None, ""):
        raise UEFACollectorError("Match row is missing id, homeTeam.id, or awayTeam.id")

    score = row.get("score") if isinstance(row.get("score"), Mapping) else {}
    full_time = score.get("fullTime") if isinstance(score.get("fullTime"), Mapping) else {}
    home_score = _safe_int(full_time.get("home"))
    away_score = _safe_int(full_time.get("away"))
    status = _status(row.get("status"), home_score, away_score)
    winner_side = _winner_side(home_score, away_score) if status == "completed" else None

    home_id = str(home_id_raw)
    away_id = str(away_id_raw)
    home_team = teams_by_id.get(home_id, {})
    away_team = teams_by_id.get(away_id, {})

    home_abbr = str(home_team.get("team_abbr") or home.get("tla") or home_id)
    away_abbr = str(away_team.get("team_abbr") or away.get("tla") or away_id)

    if winner_side == "home":
        winner_id, winner_abbr = home_id, home_abbr
    elif winner_side == "away":
        winner_id, winner_abbr = away_id, away_abbr
    elif winner_side == "tie":
        winner_id, winner_abbr = None, "TIE"
    else:
        winner_id, winner_abbr = None, None

    game_date, eastern_time, kickoff_utc = _kickoff_fields(row.get("utcDate"))
    season_node = row.get("season") if isinstance(row.get("season"), Mapping) else {}
    season_start = season_node.get("startDate")
    season = _safe_int(str(season_start)[:4]) if season_start else None

    return {
        "game_id": str(game_id),
        "sport": SPORT,
        "league": league_name,
        "season": season,
        "week": _safe_int(row.get("matchday")),
        "game_type": row.get("stage"),
        "game_date": game_date,
        "game_time_eastern": eastern_time,
        "kickoff_utc": kickoff_utc,
        "home_team_id": home_id,
        "home_team_abbr": home_abbr,
        "home_team_name": home_team.get("team_name") or home.get("name"),
        "away_team_id": away_id,
        "away_team_abbr": away_abbr,
        "away_team_name": away_team.get("team_name") or away.get("name"),
        "home_score": home_score,
        "away_score": away_score,
        "status": status,
        "winner_team_id": winner_id,
        "winner_team_abbr": winner_abbr,
        "location": row.get("venue"),
        "source": SOURCE_NAME,
    }


class UEFACollector:
    """Load UEFA teams and matches from football-data.org and normalize them."""

    def __init__(
        self,
        api_token: str | None = None,
        competition_code: str = DEFAULT_COMPETITION_CODE,
        team_loader: Callable[[int], Any] | None = None,
        match_loader: Callable[[int], Any] | None = None,
    ) -> None:
        self.api_token = api_token or os.getenv("FOOTBALL_DATA_API_TOKEN")
        self.competition_code = competition_code.upper()
        self._team_loader = team_loader
        self._match_loader = match_loader

    def _request_json(self, path: str, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if not self.api_token:
            raise UEFACollectorError(
                "Missing football-data.org API token. Set FOOTBALL_DATA_API_TOKEN."
            )

        query = urlencode({k: v for k, v in (params or {}).items() if v is not None})
        url = f"{BASE_URL}{path}"
        if query:
            url = f"{url}?{query}"

        request = Request(
            url,
            headers={
                "X-Auth-Token": self.api_token,
                "Accept": "application/json",
                "User-Agent": "SportsBetting_491/1.0",
            },
        )

        try:
            with urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8")
            except Exception:
                pass
            raise UEFACollectorError(
                f"football-data.org returned HTTP {exc.code}: {detail or exc.reason}"
            ) from exc
        except URLError as exc:
            raise UEFACollectorError(f"Could not reach football-data.org: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise UEFACollectorError("football-data.org returned invalid JSON") from exc

        if not isinstance(payload, dict):
            raise UEFACollectorError("football-data.org returned an unexpected response")
        return payload

    def _competition_name(self, payload: Mapping[str, Any]) -> str:
        competition = payload.get("competition")
        if isinstance(competition, Mapping) and competition.get("name"):
            return str(competition["name"])
        if self.competition_code == "CL":
            return DEFAULT_LEAGUE_NAME
        return f"UEFA {self.competition_code}"

    def _load_teams_payload(self, season: int) -> Any:
        if self._team_loader:
            return self._team_loader(season)
        return self._request_json(
            f"/competitions/{self.competition_code}/teams",
            {"season": season},
        )

    def _load_matches_payload(self, season: int) -> Any:
        if self._match_loader:
            return self._match_loader(season)
        return self._request_json(
            f"/competitions/{self.competition_code}/matches",
            {"season": season},
        )

    @staticmethod
    def _validate_season(season: int) -> None:
        if season < 1955 or season > 2100:
            raise ValueError("season must be a four-digit UEFA season starting year")

    def get_teams(self, season: int) -> list[dict[str, Any]]:
        self._validate_season(season)
        try:
            payload = self._load_teams_payload(season)
            if not isinstance(payload, Mapping):
                raise UEFACollectorError("UEFA team source returned an unexpected response")
            raw_teams = payload.get("teams")
            if not isinstance(raw_teams, list):
                raise UEFACollectorError("UEFA team response is missing the teams list")
            league_name = self._competition_name(payload)
            teams = [normalize_team(row, league_name) for row in raw_teams]
        except UEFACollectorError:
            raise
        except Exception as exc:
            raise UEFACollectorError(f"Failed to load UEFA teams for {season}: {exc}") from exc

        if not teams:
            raise UEFACollectorError(f"UEFA team source returned zero teams for {season}")
        return teams

    def get_games(self, season: int) -> list[dict[str, Any]]:
        self._validate_season(season)
        teams = self.get_teams(season)
        teams_by_id = {team["team_id"]: team for team in teams}

        try:
            payload = self._load_matches_payload(season)
            if not isinstance(payload, Mapping):
                raise UEFACollectorError("UEFA match source returned an unexpected response")
            raw_matches = payload.get("matches")
            if not isinstance(raw_matches, list):
                raise UEFACollectorError("UEFA match response is missing the matches list")
            league_name = self._competition_name(payload)
            games = [normalize_game(row, teams_by_id, league_name) for row in raw_matches]
        except UEFACollectorError:
            raise
        except Exception as exc:
            raise UEFACollectorError(f"Failed to load UEFA matches for {season}: {exc}") from exc

        if not games:
            raise UEFACollectorError(f"UEFA match source returned zero matches for {season}")
        return games

    def collect(self, season: int) -> CollectorResult:
        self._validate_season(season)
        teams = self.get_teams(season)
        teams_by_id = {team["team_id"]: team for team in teams}

        try:
            payload = self._load_matches_payload(season)
            if not isinstance(payload, Mapping):
                raise UEFACollectorError("UEFA match source returned an unexpected response")
            raw_matches = payload.get("matches")
            if not isinstance(raw_matches, list):
                raise UEFACollectorError("UEFA match response is missing the matches list")
            league_name = self._competition_name(payload)
            games = [normalize_game(row, teams_by_id, league_name) for row in raw_matches]
        except UEFACollectorError:
            raise
        except Exception as exc:
            raise UEFACollectorError(f"Failed to load UEFA matches for {season}: {exc}") from exc

        if not games:
            raise UEFACollectorError(f"UEFA match source returned zero matches for {season}")
        return CollectorResult(teams=teams, games=games)


def write_csv(rows: Iterable[Mapping[str, Any]], path: str | Path) -> Path:
    rows = list(rows)
    if not rows:
        raise UEFACollectorError("Cannot write an empty dataset")

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def validate_result(result: CollectorResult) -> list[str]:
    """Run lightweight data-quality checks and return human-readable results."""
    checks: list[str] = []

    if len(result.teams) < 2:
        raise UEFACollectorError(f"Expected multiple UEFA teams, got {len(result.teams)}")
    checks.append(f"PASS: collected {len(result.teams)} UEFA teams")

    team_ids = [row["team_id"] for row in result.teams]
    if len(team_ids) != len(set(team_ids)):
        raise UEFACollectorError("Duplicate team_id values detected")
    checks.append("PASS: team_id values are unique")

    game_ids = [row["game_id"] for row in result.games]
    if len(game_ids) != len(set(game_ids)):
        raise UEFACollectorError("Duplicate game_id values detected")
    checks.append("PASS: game_id values are unique")

    required_game_fields = {
        "game_id",
        "season",
        "home_team_id",
        "away_team_id",
        "status",
        "kickoff_utc",
    }
    known_team_ids = set(team_ids)
    for index, game in enumerate(result.games):
        missing = [field for field in required_game_fields if game.get(field) in (None, "")]
        if missing:
            raise UEFACollectorError(f"Game {index} missing required fields: {missing}")
        if game["home_team_id"] not in known_team_ids or game["away_team_id"] not in known_team_ids:
            raise UEFACollectorError(f"Game {index} references a team not found in the team dataset")
    checks.append("PASS: every game contains required normalized fields and known teams")

    completed = [game for game in result.games if game["status"] == "completed"]
    for game in completed:
        if game["home_score"] is None or game["away_score"] is None:
            raise UEFACollectorError("Completed game is missing a score")
    checks.append(f"PASS: {len(completed)} completed games have final scores")

    return checks


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect normalized UEFA team and match data")
    parser.add_argument(
        "--season",
        type=int,
        required=True,
        help="UEFA season starting year, e.g. 2026 for the 2026-27 season",
    )
    parser.add_argument(
        "--competition-code",
        default=DEFAULT_COMPETITION_CODE,
        help="football-data.org competition code (default: CL for Champions League)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/development",
        help="Directory for normalized CSV output",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    collector = UEFACollector(competition_code=args.competition_code)

    try:
        result = collector.collect(args.season)
        checks = validate_result(result)
        output_dir = Path(args.output_dir)
        prefix = args.competition_code.lower()
        teams_path = write_csv(result.teams, output_dir / f"uefa_{prefix}_teams.csv")
        games_path = write_csv(result.games, output_dir / f"uefa_{prefix}_games_{args.season}.csv")
    except (UEFACollectorError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"Collected {len(result.teams)} UEFA teams -> {teams_path}")
    print(f"Collected {len(result.games)} UEFA matches -> {games_path}")
    for check in checks:
        print(check)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
