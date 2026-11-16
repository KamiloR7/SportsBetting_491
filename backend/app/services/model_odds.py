"""Local model probabilities to explicitly margined virtual-point prices."""
import hashlib
import json
import math
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from functools import lru_cache
from pathlib import Path
import numpy as np
import pandas as pd
from fastapi import HTTPException
from sqlalchemy import select, insert, update
from app.ml.predict_multisport import load_trusted_baseline
from app.ml.features.engineer_multisport_features import FEATURE_COLUMNS
from app.ml.training.train_sport_aware_baseline import SPORT_CLASSES
from app.database.betting_tables import outcomes
from app.database.model_odds_tables import quotes


def decimal_prices(probabilities, margin=0.05):
    if not probabilities or not 0 <= margin <= 0.20:
        raise ValueError("Invalid pricing margin or probabilities")
    values = list(probabilities.values())
    if any(not math.isfinite(p) or p <= 0 or p >= 1 for p in values) or not math.isclose(sum(values), 1, abs_tol=1e-8):
        raise ValueError("Pricing requires a normalized, nondegenerate probability distribution")
    factor = Decimal("1") + Decimal(str(margin))
    prices = {}
    for name, probability in probabilities.items():
        fair_adjusted = Decimal("1") / (Decimal(str(probability)) * factor)
        bounded = max(Decimal("1.01"), min(Decimal("1000.00"), fair_adjusted))
        prices[name] = bounded.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    return prices



class MarketModelRegistry:
    def __init__(self, directory):
        self.directory = Path(directory)
        self._cache = {}

    def get(self, sport):
        manifest = json.loads((self.directory / "manifest.json").read_text())
        relative = manifest["sports"][sport]["artifact"]
        path = (self.directory / relative).resolve()
        if not path.is_relative_to(self.directory.resolve()):
            raise ValueError("Invalid configured artifact path")
        key = (sport, relative)
        if key not in self._cache:
            model, metadata = load_trusted_baseline(path)
            if metadata.get("sport") != sport or metadata.get("feature_columns") != FEATURE_COLUMNS:
                raise ValueError("Incompatible market model metadata")
            if set(model.classes_) != SPORT_CLASSES[sport]:
                raise ValueError("Incompatible market model outcomes")
            self._cache[key] = model, metadata
        return self._cache[key]

    def predict(self, context):
        model, metadata = self.get(context.sport)
        if pd.Timestamp(metadata["train_end"]) >= pd.Timestamp(context.feature_cutoff):
            raise ValueError("Pricing model was trained after this match; historical replay is required")
        frame = pd.DataFrame([context.features], columns=FEATURE_COLUMNS)
        values = model.predict_proba(frame)[0]
        if not np.isfinite(values).all():
            raise ValueError("Invalid model probability output")
        probabilities = {str(name).removesuffix("_win"): float(p) for name, p in zip(model.classes_, values)}
        # The pricing validation also checks range and normalization.
        decimal_prices(probabilities, 0)
        return probabilities, metadata


@lru_cache(maxsize=4)
def market_registry(directory):
    return MarketModelRegistry(directory)


def configured_registry():
    from app.core.config import settings
    return market_registry(str(settings.MARKET_MODEL_DIRECTORY))


def latest_quote(db, market_id):
    return db.execute(select(quotes).where(quotes.c.market_id == market_id).order_by(quotes.c.id.desc()).limit(1)).mappings().first()


def ensure_quote(db, match, market):
    """Caller holds match then market locks; transaction and commit stay with caller."""
    from app.core.config import settings
    from app.services.prediction_service import MatchHistoryRepository
    try:
        context = MatchHistoryRepository(db).get_context(match["id"])
        registry = configured_registry()
        _, metadata = registry.get(context.sport)
        if pd.Timestamp(metadata["train_end"]) >= pd.Timestamp(context.feature_cutoff):
            raise ValueError("The model training cutoff is incompatible with this match")
        current = latest_quote(db, market["id"])
        if current:
            generated = current["generated_at"]
            if isinstance(generated, str): generated = datetime.fromisoformat(generated)
            if generated.tzinfo is None: generated = generated.replace(tzinfo=timezone.utc)
            if current["model_version"] == metadata["artifact_version"] and float(current["margin"]) == settings.MODEL_ODDS_MARGIN and (datetime.now(timezone.utc) - generated).total_seconds() < 60:
                return current
        probabilities, metadata = registry.predict(context)
        prices = decimal_prices(probabilities, settings.MODEL_ODDS_MARGIN)
    except (ValueError, KeyError, OSError, RuntimeError) as exc:
        raise HTTPException(503, "Model-priced odds are unavailable for this match. No fallback prices are offered.") from exc
    stored = db.execute(select(outcomes).where(outcomes.c.market_id == market["id"])).mappings().all()
    if {row["selection"] for row in stored} != set(prices):
        raise HTTPException(503, "The market outcomes do not match the trained model.")
    price_values = {name: str(price) for name, price in prices.items()}
    payload = {"market_id": market["id"], "model_version": metadata["artifact_version"], "features": context.features,
               "probabilities": probabilities, "prices": price_values, "margin": settings.MODEL_ODDS_MARGIN}
    key = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    if current and current["quote_key"] == key:
        return current
    for row in stored:
        db.execute(update(outcomes).where(outcomes.c.id == row["id"]).values(decimal_odds=prices[row["selection"]]))
    return db.execute(insert(quotes).values(market_id=market["id"], quote_key=key,
        model_version=metadata["artifact_version"], training_end=pd.Timestamp(metadata["train_end"]).to_pydatetime(),
        margin=Decimal(str(settings.MODEL_ODDS_MARGIN)), probabilities=probabilities, prices=price_values,
        features=context.features, history={"home_games": context.home_history_games, "away_games": context.away_history_games})
        .returning(*quotes.c)).mappings().one()


def reconstruct_closed_quote(db, match):
    """Read-only prior-day estimate, never a recorded offer or in-play quote."""
    from app.core.config import settings
    from app.services.prediction_service import MatchHistoryRepository
    try:
        context = MatchHistoryRepository(db).get_context(match["id"])
        registry = configured_registry()
        _, metadata = registry.get(context.sport)
        if pd.Timestamp(metadata["train_end"]) >= pd.Timestamp(context.feature_cutoff):
            raise ValueError("Model includes results from the target day or later")
        probabilities, metadata = registry.predict(context)
        prices = decimal_prices(probabilities, settings.MODEL_ODDS_MARGIN)
    except (ValueError, KeyError, OSError, RuntimeError) as exc:
        raise HTTPException(503, "A prior-day model estimate is unavailable for this match.") from exc
    return {"model_version": metadata["artifact_version"], "margin": settings.MODEL_ODDS_MARGIN,
            "probabilities": probabilities, "prices": {key:str(value) for key,value in prices.items()},
            "generated_at": datetime.now(timezone.utc)}
