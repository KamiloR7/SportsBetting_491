"""Season-scoped, availability-aware historical features for NFL, MLB and EPL."""
from __future__ import annotations

from dataclasses import dataclass
from math import nan
from statistics import fmean
from typing import Any, Iterable, Mapping

import pandas as pd

from app.ml.features.chronological_dataset import build_chronological_dataset
from app.ml.features.outcome_labels import label_match_outcome

SCHEMA_VERSION = "historical_sport_features_v1"
SUPPORTED_SPORTS = {"NFL", "MLB", "EPL"}
METADATA_COLUMNS = [
    "game_id", "source_game_id", "source", "season", "source_season", "sport",
    "game_date", "start_time", "feature_as_of", "result_available_at",
    "home_team", "away_team",
]
SUMMARY_FIELDS = ["matches", "win_rate", "avg_scored", "avg_conceded", "avg_margin"]


def feature_columns(sport: str) -> list[str]:
    """Ordered numeric allowlist. Metadata and outcome are never predictors."""
    if not isinstance(sport, str) or sport.upper() not in SUPPORTED_SPORTS:
        raise ValueError("Expected sport NFL, MLB, or EPL")
    sport = sport.upper()
    columns = []
    for side in ("home", "away"):
        fields = [f"season_{name}" for name in SUMMARY_FIELDS]
        fields += ["season_wins", "season_losses"]
        if sport == "NFL":
            fields += ["season_ties"]
        if sport == "EPL":
            fields += ["season_draws", "season_points_per_match"]
        for window in (5, 10):
            fields += [f"recent{window}_{name}" for name in SUMMARY_FIELDS]
        fields += [f"venue_{name}" for name in SUMMARY_FIELDS]
        fields += ["opponent_win_rate", "opponent_observations"]
        columns += [f"{side}_{name}" for name in fields]
    return columns


@dataclass
class SportFeatureDataset:
    """Chronological partitions with explicit predictors and separate labels."""

    train: pd.DataFrame
    test: pd.DataFrame
    sport: str
    feature_columns: list[str]
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class _TeamResult:
    opponent: str
    venue: str
    scored: int
    conceded: int

    @property
    def won(self) -> bool:
        return self.scored > self.conceded


def _summary(history: list[_TeamResult]) -> dict[str, float | int]:
    if not history:
        return {"matches": 0, **{name: nan for name in SUMMARY_FIELDS[1:]}}
    return {
        "matches": len(history),
        "win_rate": fmean(game.won for game in history),
        "avg_scored": fmean(game.scored for game in history),
        "avg_conceded": fmean(game.conceded for game in history),
        "avg_margin": fmean(game.scored - game.conceded for game in history),
    }


def _team_features(
    team: str, venue: str, histories: dict[str, list[_TeamResult]], sport: str,
) -> dict[str, float | int]:
    history = histories.get(team, [])
    values = {f"season_{key}": value for key, value in _summary(history).items()}
    wins = sum(game.won for game in history)
    losses = sum(game.scored < game.conceded for game in history)
    draws = len(history) - wins - losses
    values.update(season_wins=wins, season_losses=losses)
    if sport == "NFL":
        values["season_ties"] = draws
    if sport == "EPL":
        values["season_draws"] = draws
        values["season_points_per_match"] = (3 * wins + draws) / len(history) if history else nan
    for window in (5, 10):
        values.update({f"recent{window}_{key}": value
                       for key, value in _summary(history[-window:]).items()})
    values.update({f"venue_{key}": value for key, value in
                   _summary([game for game in history if game.venue == venue]).items()})

    # Raw outcomes only: no recursively calculated ratings. Exclude an opponent's
    # games against this focal team so strength is not a restatement of its form.
    opponent_rates = {}
    for game in history:
        if game.opponent not in opponent_rates:
            other_games = [result for result in histories.get(game.opponent, [])
                           if result.opponent != team]
            opponent_rates[game.opponent] = (
                fmean(result.won for result in other_games) if other_games else None
            )
    rates = [opponent_rates[game.opponent] for game in history
             if opponent_rates[game.opponent] is not None]
    values["opponent_win_rate"] = fmean(rates) if rates else nan
    values["opponent_observations"] = len(rates)
    return values


def build_sport_feature_dataset(
    records: Iterable[Mapping[str, Any]], sport: str, test_fraction: float = 0.2,
) -> SportFeatureDataset:
    """Validate canonical history and construct pre-match train/test features.

    All statistics reset at season boundaries and exclude the entire target UTC
    day. No imputation or scaling is fitted here. See the ordered feature allowlist
    before passing these frames (which include outcome labels) to a model.
    """
    columns = feature_columns(sport)
    dataset = build_chronological_dataset(records, sport, test_fraction)
    games = pd.concat([dataset.train, dataset.test], ignore_index=True)
    # Whole-day splits normalize game_date; retain actual kickoff for ordering
    # previous-day doubleheaders within rolling windows.
    ordered_history = games.sort_values(["start_time", "game_id"])
    rows = []
    for game in games.to_dict("records"):
        eligible = ordered_history[
            (ordered_history["season"] == game["season"])
            & (ordered_history["game_date"] < game["game_date"])
            & (ordered_history["result_available_at"] <= game["feature_as_of"])
        ]
        histories: dict[str, list[_TeamResult]] = {}
        for previous in eligible.to_dict("records"):
            for side, opponent in (("home", "away"), ("away", "home")):
                histories.setdefault(previous[f"{side}_team"], []).append(_TeamResult(
                    opponent=previous[f"{opponent}_team"], venue=side,
                    scored=previous[f"{side}_score"], conceded=previous[f"{opponent}_score"],
                ))
        row = {key: game[key] for key in METADATA_COLUMNS}
        for side in ("home", "away"):
            row.update({f"{side}_{key}": value for key, value in _team_features(
                game[f"{side}_team"], side, histories, dataset.sport,
            ).items()})
        row["outcome"] = label_match_outcome(
            dataset.sport, game["home_score"], game["away_score"], "FINAL",
        )
        rows.append(row)
    features = pd.DataFrame(rows, columns=METADATA_COLUMNS + columns + ["outcome"])
    boundary = len(dataset.train)
    return SportFeatureDataset(
        train=features.iloc[:boundary].reset_index(drop=True),
        test=features.iloc[boundary:].reset_index(drop=True),
        sport=dataset.sport, feature_columns=columns,
    )
