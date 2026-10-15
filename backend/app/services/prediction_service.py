"""Prediction orchestration from stored matchup history to API response."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ml.features.engineer_multisport_features import FEATURE_COLUMNS
from app.ml.predict_multisport import predict_outcomes
from app.schemas.predictions import (
    PredictionHistory,
    PredictionProbabilities,
    PredictionResponse,
)
from app.services.model_registry import ModelRegistry, ModelRegistryError, SUPPORTED_SPORTS


class PredictionServiceError(RuntimeError):
    """Base error for controlled prediction failures."""


class MatchNotFoundError(PredictionServiceError):
    pass


class UnsupportedSportError(PredictionServiceError):
    pass


class PredictionUnavailableError(PredictionServiceError):
    pass


@dataclass(frozen=True)
class MatchContext:
    match_id: int
    sport: str
    home_team_id: int
    home_team_name: str
    away_team_id: int
    away_team_name: str
    features: dict[str, float]
    home_history_games: int
    away_history_games: int


class MatchHistoryRepository:
    """Build leakage-safe features from final games before a selected match."""

    def __init__(self, db: Session):
        self.db = db

    def get_context(self, match_id: int) -> MatchContext:
        match = self.db.execute(
            text(
                """
                SELECT m.id, m.start_time, l.abbreviation AS sport,
                       ht.id AS home_team_id, ht.name AS home_team_name,
                       at.id AS away_team_id, at.name AS away_team_name
                FROM matches m
                JOIN leagues l ON l.id = m.league_id
                JOIN teams ht ON ht.id = m.home_team_id
                JOIN teams at ON at.id = m.away_team_id
                WHERE m.id = :match_id
                """
            ),
            {"match_id": match_id},
        ).first()
        if match is None:
            raise MatchNotFoundError(f"Match {match_id} was not found")

        sport = (match.sport or "").upper()
        if sport not in SUPPORTED_SPORTS:
            raise UnsupportedSportError(f"Predictions are not supported for {sport or 'this league'}")

        games = self.db.execute(
            text(
                """
                SELECT home_team_id, away_team_id, home_score, away_score
                FROM matches
                WHERE status = 'final'
                  AND start_time < :start_time
                  AND (home_team_id IN (:home_team_id, :away_team_id)
                       OR away_team_id IN (:home_team_id, :away_team_id))
                ORDER BY start_time, id
                """
            ),
            {
                "start_time": match.start_time,
                "home_team_id": match.home_team_id,
                "away_team_id": match.away_team_id,
            },
        ).all()

        home_stats = self._team_stats(games, match.home_team_id)
        away_stats = self._team_stats(games, match.away_team_id)
        features = {
            "home_win_rate": home_stats[1] / home_stats[0] if home_stats[0] else 0.0,
            "away_win_rate": away_stats[1] / away_stats[0] if away_stats[0] else 0.0,
            "home_avg_score": home_stats[2] / home_stats[0] if home_stats[0] else 0.0,
            "away_avg_score": away_stats[2] / away_stats[0] if away_stats[0] else 0.0,
            "home_avg_allowed": home_stats[3] / home_stats[0] if home_stats[0] else 0.0,
            "away_avg_allowed": away_stats[3] / away_stats[0] if away_stats[0] else 0.0,
        }
        return MatchContext(
            match_id=match.id,
            sport=sport,
            home_team_id=match.home_team_id,
            home_team_name=match.home_team_name,
            away_team_id=match.away_team_id,
            away_team_name=match.away_team_name,
            features=features,
            home_history_games=home_stats[0],
            away_history_games=away_stats[0],
        )

    @staticmethod
    def _team_stats(games, team_id: int) -> tuple[int, int, int, int]:
        count = wins = scored = allowed = 0
        for game in games:
            if game.home_team_id == team_id:
                team_score, opponent_score = game.home_score, game.away_score
            elif game.away_team_id == team_id:
                team_score, opponent_score = game.away_score, game.home_score
            else:
                continue
            if team_score is None or opponent_score is None:
                continue
            count += 1
            wins += int(team_score > opponent_score)
            scored += team_score
            allowed += opponent_score
        return count, wins, scored, allowed


class PredictionService:
    def __init__(self, registry: ModelRegistry, repository: MatchHistoryRepository):
        self.registry = registry
        self.repository = repository

    def predict(self, match_id: int) -> PredictionResponse:
        context = self.repository.get_context(match_id)
        try:
            model, metadata = self.registry.get(context.sport)
            frame = pd.DataFrame([context.features], columns=FEATURE_COLUMNS)
            result = predict_outcomes(model, frame).iloc[0]
        except (ModelRegistryError, ValueError, TypeError) as exc:
            raise PredictionUnavailableError(str(exc)) from exc

        home_probability = float(result["probability_home_win"])
        not_home_probability = float(result["probability_not_home_win"])
        home_win = int(result["predicted_outcome"]) == 1
        return PredictionResponse(
            match_id=context.match_id,
            sport=context.sport,
            home_team_id=context.home_team_id,
            home_team_name=context.home_team_name,
            away_team_id=context.away_team_id,
            away_team_name=context.away_team_name,
            predicted_outcome="HOME_WIN" if home_win else "NOT_HOME_WIN",
            predicted_team_id=context.home_team_id if home_win else None,
            predicted_team_name=context.home_team_name if home_win else None,
            probabilities=PredictionProbabilities(
                home_win=home_probability,
                not_home_win=not_home_probability,
            ),
            confidence=max(home_probability, not_home_probability),
            model_version=str(metadata.get("artifact_version", "unversioned")),
            history=PredictionHistory(
                home_games=context.home_history_games,
                away_games=context.away_history_games,
            ),
        )


@lru_cache(maxsize=1)
def get_model_registry() -> ModelRegistry:
    from app.core.config import settings

    return ModelRegistry.from_directory(settings.MODEL_DIRECTORY)


def get_prediction_service(db: Session) -> PredictionService:
    return PredictionService(get_model_registry(), MatchHistoryRepository(db))
