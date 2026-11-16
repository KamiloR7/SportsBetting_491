"""Audit saved held-out predictions without changing model weights."""
import json
from pathlib import Path
import numpy as np
from app.ml.features.prepare_multisport_data import load_all_datasets
from app.ml.features.engineer_multisport_features import create_features, chronological_split, FEATURE_COLUMNS
from app.ml.predict_multisport import load_trusted_baseline, predict_outcomes

def main():
    root=Path(__file__).resolve().parents[3]
    datasets=load_all_datasets(root/"data/raw")
    report=json.loads((root/"build/sprint2-models/report.json").read_text())
    evidence={"protocol":"Fixed model; whole-date chronological holdout; expanding prior-day outcomes. No tuning on holdout.","sports":{}}
    for sport,games in datasets.items():
        features=create_features(games); train,test=chronological_split(features)
        assert train.game_date.max()<test.game_date.min()
        info=report["sports"][sport]
        directory=Path(info["artifact_directory"])
        if not directory.is_absolute(): directory=root/directory
        model,metadata=load_trusted_baseline(directory/f"{sport.lower()}_baseline.pkl")
        np.testing.assert_allclose(model.named_steps["scaler"].mean_,train[FEATURE_COLUMNS].mean().to_numpy(),atol=1e-12)
        # Changing a target game's result and all later results cannot change that game's features.
        for index in [test.index[0],test.index[-1]]:
            date=features.loc[index,"game_date"]
            changed=games.copy(); mask=changed.game_date.dt.normalize()>=date
            changed.loc[mask,"home_score"]=999; changed.loc[mask,"away_score"]=0
            altered=create_features(changed)
            np.testing.assert_array_equal(features.loc[index,FEATURE_COLUMNS].to_numpy(),altered.loc[index,FEATURE_COLUMNS].to_numpy())
        examples=[]
        for index in test.index[:2]:
            frame=features.loc[[index]]
            result=predict_outcomes(model,frame).iloc[0]
            actual=int(frame.outcome.iloc[0])
            examples.append({"game_id":str(frame.game_id.iloc[0]),"date":str(frame.game_date.iloc[0]),"home":str(frame.home_team.iloc[0]),"away":str(frame.away_team.iloc[0]),"p_home_win":float(result.probability_home_win),"predicted":int(result.predicted_outcome),"actual":actual})
        evidence["sports"][sport]={"train_rows":len(train),"holdout_rows":len(test),"train_end":str(train.game_date.max()),"test_start":str(test.game_date.min()),"score_perturbation_passed":True,"scaler_train_only_passed":True,"model_version":metadata["artifact_version"],"examples":examples,"metrics":info["metrics"]}
    destination=root/"build/sprint5-holdout-audit.json"
    destination.write_text(json.dumps(evidence,indent=2)+"\n")
    print(destination)
    for sport,item in evidence["sports"].items(): print(sport,item["examples"])

if __name__=="__main__":main()
