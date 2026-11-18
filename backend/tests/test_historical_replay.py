import pandas as pd
import numpy as np
import pytest
from app.services.historical_replay import replay_training_features, fit_replay
from app.ml.features.engineer_multisport_features import FEATURE_COLUMNS

def games():
    return pd.DataFrame([{"game_id":str(i),"game_date":f"2025-01-01T12:00:00Z","home_team":"A","away_team":"B","home_score":3 if i%2 else 1,"away_score":2} for i in range(45)]).assign(game_date=pd.date_range("2025-01-01",periods=45,tz="UTC"))

def test_target_same_day_and_future_results_cannot_affect_replay():
    data=games();cutoff=data.game_date.iloc[35]
    before=replay_training_features(data,cutoff)
    changed=data.copy();changed.loc[changed.game_date>=cutoff,"home_score"]=999
    after=replay_training_features(changed,cutoff)
    pd.testing.assert_frame_equal(before,after)
    assert before.game_date.max()<cutoff
    assert len(before)==35
    model=fit_replay(before.to_json(orient="split",date_format="iso"))
    np.testing.assert_allclose(model.named_steps["scaler"].mean_,before[FEATURE_COLUMNS].mean())

def test_replay_rejects_tiny_training_history():
    data=games()
    with pytest.raises(ValueError,match="30 earlier"): replay_training_features(data,data.game_date.iloc[10])


@pytest.mark.parametrize("sport,home_score,away_score",[("NBA",2,1),("MLB",None,1)])
def test_invalid_replay_target_is_rejected_before_training(sport,home_score,away_score):
    from unittest.mock import MagicMock
    from fastapi import HTTPException
    from app.services.historical_replay import replay_match
    db=MagicMock()
    db.execute.return_value.mappings.return_value.first.return_value={"sport":sport,"status":"final","home_score":home_score,"away_score":away_score}
    with pytest.raises(HTTPException) as error: replay_match(db,1)
    assert error.value.status_code==422
    assert db.execute.call_count==1
