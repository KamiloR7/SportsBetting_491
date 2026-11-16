"""Reconstruct a prediction using only matches from before the selected UTC day."""
import hashlib
from datetime import datetime, timezone
from functools import lru_cache
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sqlalchemy import text
from fastapi import HTTPException
from app.ml.features.engineer_multisport_features import create_features, FEATURE_COLUMNS
from app.services.prediction_service import MatchHistoryRepository, PredictionService

def replay_training_features(games, cutoff):
    data=games.copy()
    dates=pd.to_datetime(data["game_date"],utc=True)
    prior=data.loc[dates.dt.normalize()<pd.Timestamp(cutoff)].copy()
    if len(prior)<30: raise ValueError("Historical replay needs at least 30 earlier league games. Choose a more recent completed match.")
    frame=create_features(prior)
    if frame.outcome.nunique()<2: raise ValueError("Earlier results do not contain both outcome classes.")
    return frame

@lru_cache(maxsize=24)
def fit_replay(records):
    import io
    frame=pd.read_json(io.StringIO(records),orient="split")
    model=Pipeline([("scaler",StandardScaler()),("classifier",LogisticRegression(max_iter=1000,random_state=42))])
    model.fit(frame[FEATURE_COLUMNS],frame.outcome)
    return model

def replay_match(db,match_id):
    target=db.execute(text("SELECT m.start_time,m.status,m.home_score,m.away_score,l.abbreviation AS sport FROM matches m JOIN leagues l ON l.id=m.league_id WHERE m.id=:id"),{"id":match_id}).mappings().first()
    if target is None: raise HTTPException(404,"Match not found.")
    if target["sport"] not in {"NFL","MLB","EPL"}: raise HTTPException(422,"Historical replay is not available for this league.")
    if target["home_score"] is None or target["away_score"] is None:
        raise HTTPException(422,"This match does not have a complete final score.")
    if target["status"]!="final": raise HTTPException(422,"Historical replay is available for completed matches only.")
    kickoff=target["start_time"]
    if isinstance(kickoff,str): kickoff=datetime.fromisoformat(kickoff.replace("Z","+00:00"))
    cutoff=kickoff.astimezone(timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0)
    from app.ml.train_local_match_models import completed_games
    games=completed_games(db,target["sport"])
    try: frame=replay_training_features(games,cutoff)
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc
    records=frame.to_json(orient="split",date_format="iso")
    model=fit_replay(records)
    version="replay-"+hashlib.sha256(records.encode()).hexdigest()[:16]
    class Registry:
        def get(self,sport): return model,{"artifact_version":version}
    result=PredictionService(Registry(),MatchHistoryRepository(db)).predict(match_id).model_dump()
    actual="HOME_WIN" if target["home_score"]>target["away_score"] else "NOT_HOME_WIN"
    return {**result,"mode":"historical_replay","training_games":len(frame),"training_end":frame.game_date.max().isoformat(),"feature_cutoff":cutoff.isoformat(),"actual_outcome":actual,"correct":result["predicted_outcome"]==actual,"home_score":target["home_score"],"away_score":target["away_score"]}
