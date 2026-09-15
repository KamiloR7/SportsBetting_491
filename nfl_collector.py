"""NFL team and match collector for the multi-sport prediction project.

Primary source: nflverse via the ``nflreadpy`` Python package.

The collector keeps source retrieval separate from normalization so the same
multi-sport schema can later be used for MLB and EPL collectors.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
from zoneinfo import ZoneInfo

SOURCE_NAME = "nflverse/nflreadpy"
SPORT = "NFL"
LEAGUE = "NFL"
EASTERN = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")


class NFLCollectorError(RuntimeError):
    """Raised when NFL source data cannot be loaded or normalized."""


@dataclass(frozen=True)
class CollectorResult:
    teams: list[dict[str, Any]]
    games: list[dict[str, Any]]


def _records(frame: Any) -> list[dict[str, Any]]:
    """Convert a supported dataframe-like object to a list of dictionaries."""
    if hasattr(frame, "to_dicts"):  # Polars
        return list(frame.to_dicts())
    if hasattr(frame, "to_dict"):  # Pandas
        try:
            return list(frame.to_dict(orient="records"))
        except TypeError:
            pass
    if isinstance(frame, list):
        if all(isinstance(row, Mapping) for row in frame):
            return [dict(row) for row in frame]
    raise NFLCollectorError("Unsupported dataframe type returned by NFL data source")


def _safe_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise NFLCollectorError(f"Expected integer-compatible value, got {value!r}") from exc


def _kickoff_utc(gameday: Any, gametime: Any) -> str | None:
    """Combine nflverse gameday + Eastern gametime and return UTC ISO-8601."""
    if not gameday:
        return None
    date_text = str(gameday)
    time_text = str(gametime) if gametime else "00:00"
    try:
        local_dt = datetime.strptime(f"{date_text} {time_text}", "%Y-%m-%d %H:%M").replace(
            tzinfo=EASTERN
        )
    except ValueError as exc:
        raise NFLCollectorError(
            f"Could not parse gameday/gametime: {date_text!r} {time_text!r}"
        ) from exc
    return local_dt.astimezone(UTC).isoformat()


def normalize_team(row: Mapping[str, Any]) -> dict[str, Any]:
    """Map one nflverse team row into the project's shared team shape."""
    team_abbr = row.get("team_abbr")
    team_name = row.get("team_name")
    if not team_abbr or not team_name:
        raise NFLCollectorError("Team row is missing team_abbr or team_name")

    return {
        "team_id": str(row.get("team_id") or team_abbr),
        "sport": SPORT,
        "league": LEAGUE,
        "team_abbr": str(team_abbr),
        "team_name": str(team_name),
        "conference": row.get("team_conf"),
        "division": row.get("team_division"),
        "source": SOURCE_NAME,
    }


def _game_outcome(home_score: int | None, away_score: int | None) -> tuple[str, str | None]:
    if home_score is None and away_score is None:
        return "scheduled", None
    if home_score is None or away_score is None:
        return "incomplete", None
    if home_score > away_score:
        return "completed", "home"
    if away_score > home_score:
        return "completed", "away"
    return "completed", "tie"


def normalize_game(
    row: Mapping[str, Any],
    teams_by_abbr: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Map one nflverse schedule row into the project's shared match shape."""
    game_id = row.get("game_id")
    home_abbr = row.get("home_team")
    away_abbr = row.get("away_team")
    if not game_id or not home_abbr or not away_abbr:
        raise NFLCollectorError("Game row is missing game_id, home_team, or away_team")

    home_score = _safe_int(row.get("home_score"))
    away_score = _safe_int(row.get("away_score"))
    status, winner_side = _game_outcome(home_score, away_score)

    home_team = teams_by_abbr.get(str(home_abbr), {})
    away_team = teams_by_abbr.get(str(away_abbr), {})
    home_id = str(home_team.get("team_id") or home_abbr)
    away_id = str(away_team.get("team_id") or away_abbr)

    if winner_side == "home":
        winner_id, winner_abbr = home_id, str(home_abbr)
    elif winner_side == "away":
        winner_id, winner_abbr = away_id, str(away_abbr)
    elif winner_side == "tie":
        winner_id, winner_abbr = None, "TIE"
    else:
        winner_id, winner_abbr = None, None

    return {
        "game_id": str(game_id),
        "sport": SPORT,
        "league": LEAGUE,
        "season": _safe_int(row.get("season")),
        "week": _safe_int(row.get("week")),
        "game_type": row.get("game_type"),
        "game_date": str(row.get("gameday")) if row.get("gameday") else None,
        "game_time_eastern": str(row.get("gametime")) if row.get("gametime") else None,
        "kickoff_utc": _kickoff_utc(row.get("gameday"), row.get("gametime")),
        "home_team_id": home_id,
        "home_team_abbr": str(home_abbr),
        "home_team_name": home_team.get("team_name"),
        "away_team_id": away_id,
        "away_team_abbr": str(away_abbr),
        "away_team_name": away_team.get("team_name"),
        "home_score": home_score,
        "away_score": away_score,
        "status": status,
        "winner_team_id": winner_id,
        "winner_team_abbr": winner_abbr,
        "location": row.get("location"),
        "source": SOURCE_NAME,
    }


class NFLCollector:
    """Loads NFL teams and schedules from nflverse and normalizes them."""

    def __init__(
        self,
        team_loader: Callable[[], Any] | None = None,
        schedule_loader: Callable[[int], Any] | None = None,
    ) -> None:
        self._team_loader = team_loader
        self._schedule_loader = schedule_loader

    def _load_nflreadpy(self) -> Any:
        try:
            import nflreadpy as nfl  # type: ignore
        except ImportError as exc:
            raise NFLCollectorError(
                "nflreadpy is not installed. Run: pip install nflreadpy"
            ) from exc
        return nfl

    def get_teams(self) -> list[dict[str, Any]]:
        try:
            raw = self._team_loader() if self._team_loader else self._load_nflreadpy().load_teams()
            teams = [normalize_team(row) for row in _records(raw)]
        except NFLCollectorError:
            raise
        except Exception as exc:
            raise NFLCollectorError(f"Failed to load NFL teams: {exc}") from exc

        if not teams:
            raise NFLCollectorError("NFL team source returned zero teams")
        return teams

    def get_games(self, season: int) -> list[dict[str, Any]]:
        if season < 1920 or season > 2100:
            raise ValueError("season must be a four-digit NFL season year")

        teams = self.get_teams()
        teams_by_abbr = {team["team_abbr"]: team for team in teams}
        try:
            raw = (
                self._schedule_loader(season)
                if self._schedule_loader
                else self._load_nflreadpy().load_schedules(season)
            )
            games = [normalize_game(row, teams_by_abbr) for row in _records(raw)]
        except NFLCollectorError:
            raise
        except Exception as exc:
            raise NFLCollectorError(f"Failed to load NFL schedule for {season}: {exc}") from exc

        if not games:
            raise NFLCollectorError(f"NFL schedule source returned zero games for {season}")
        return games

    def collect(self, season: int) -> CollectorResult:
        teams = self.get_teams()
        teams_by_abbr = {team["team_abbr"]: team for team in teams}
        try:
            raw = (
                self._schedule_loader(season)
                if self._schedule_loader
                else self._load_nflreadpy().load_schedules(season)
            )
            games = [normalize_game(row, teams_by_abbr) for row in _records(raw)]
        except NFLCollectorError:
            raise
        except Exception as exc:
            raise NFLCollectorError(f"Failed to load NFL schedule for {season}: {exc}") from exc

        if not games:
            raise NFLCollectorError(f"NFL schedule source returned zero games for {season}")
        return CollectorResult(teams=teams, games=games)


def write_csv(rows: Iterable[Mapping[str, Any]], path: str | Path) -> Path:
    rows = list(rows)
    if not rows:
        raise NFLCollectorError("Cannot write an empty dataset")
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
    if len(result.teams) != 32:
        raise NFLCollectorError(f"Expected 32 current NFL teams, got {len(result.teams)}")
    checks.append("PASS: exactly 32 current NFL teams")

    team_ids = [row["team_id"] for row in result.teams]
    if len(team_ids) != len(set(team_ids)):
        raise NFLCollectorError("Duplicate team_id values detected")
    checks.append("PASS: team_id values are unique")

    game_ids = [row["game_id"] for row in result.games]
    if len(game_ids) != len(set(game_ids)):
        raise NFLCollectorError("Duplicate game_id values detected")
    checks.append("PASS: game_id values are unique")

    required_game_fields = {
        "game_id",
        "season",
        "week",
        "home_team_id",
        "away_team_id",
        "status",
    }
    for index, game in enumerate(result.games):
        missing = [field for field in required_game_fields if game.get(field) in (None, "")]
        if missing:
            raise NFLCollectorError(f"Game {index} missing required fields: {missing}")
    checks.append("PASS: every game contains required normalized fields")

    completed = [g for g in result.games if g["status"] == "completed"]
    for game in completed:
        if game["home_score"] is None or game["away_score"] is None:
            raise NFLCollectorError("Completed game is missing a score")
    checks.append(f"PASS: {len(completed)} completed games have final scores")
    return checks


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect normalized NFL team and match data")
    parser.add_argument("--season", type=int, required=True, help="NFL season year, e.g. 2025")
    parser.add_argument(
        "--output-dir",
        default="data/development",
        help="Directory for normalized CSV output",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    collector = NFLCollector()
    try:
        result = collector.collect(args.season)
        checks = validate_result(result)
        output_dir = Path(args.output_dir)
        teams_path = write_csv(result.teams, output_dir / "nfl_teams.csv")
        games_path = write_csv(result.games, output_dir / f"nfl_games_{args.season}.csv")
    except (NFLCollectorError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"Collected {len(result.teams)} NFL teams -> {teams_path}")
    print(f"Collected {len(result.games)} NFL games -> {games_path}")
    for check in checks:
        print(check)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
