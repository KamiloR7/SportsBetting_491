import { useCallback, useEffect, useRef, useState } from "react";
import { createPrediction } from "../services/predictions";
import { savePredictionToHistory } from "../services/predictionHistory";
const percent=value=>`${Math.round(value*100)}%`;
export default function PredictionPanel({matchId,replay=false}) {
 const [state,setState]=useState({loading:true,result:null,error:""});
 const controllerRef=useRef(null);
 const load=useCallback(()=>{
  controllerRef.current?.abort();const controller=new AbortController();controllerRef.current=controller;
  setState({loading:true,result:null,error:""});
  createPrediction(matchId,{signal:controller.signal},replay).then(result=>{
   if(controller.signal.aborted)return;
   const saved=savePredictionToHistory(result);setState({loading:false,result,error:"",historyWarning:saved?"":"Prediction ready. Browser history could not be saved."});
  }).catch(error=>{if(!controller.signal.aborted)setState({loading:false,result:null,error:error.message});});
 },[matchId,replay]);
 useEffect(()=>{const timer=setTimeout(load,0);return()=>{clearTimeout(timer);controllerRef.current?.abort();};},[load]);
 const result=state.result;
 const distribution=result?.outcome_probabilities;
 const favored=distribution ? Object.keys(distribution).reduce((a,b)=>distribution[a]>distribution[b]?a:b) : null;
 const probability=distribution ? distribution[favored] : result?.confidence;
 return <section className="prediction-panel" aria-labelledby="prediction-heading"><div className="section-kicker">VIGOR MODEL INSIGHT</div><h2 id="prediction-heading">{replay?"Historical replay":"Match forecast"}</h2><p>{replay?"Rebuilt using only results from before this match. Compare the forecast with what actually happened.":"Your pregame insight, ready automatically. Based on prior team results."}</p><button type="button" disabled={state.loading} onClick={load}>{state.loading?replay?"Rebuilding the model…":"Loading forecast…":"Refresh insight"}</button>{state.loading&&<p role="status">{replay?"Training on earlier matches only…":"Analyzing prior team results…"}</p>}{state.error&&<p role="alert">{state.error}</p>}{state.historyWarning&&<p role="status">{state.historyWarning}</p>}{result&&<div className="prediction-result" aria-live="polite"><p><strong>{distribution ? (favored==="draw"?"Draw is the leading outcome":`${favored==="home"?result.home_team_name:result.away_team_name} favored`) : result.predicted_outcome==="HOME_WIN"?`${result.home_team_name} favored`:result.sport==="EPL"?"Away win or draw favored":`${result.away_team_name} favored`}</strong></p><p>{result.home_team_name} vs {result.away_team_name} · {result.sport}</p><div className="confidence-value">{percent(probability)}<span>model probability</span></div><label>Home win · {percent(result.probabilities.home_win)}<meter min="0" max="1" value={result.probabilities.home_win}/></label>{distribution ? <div className="outcome-probabilities">{Object.entries(distribution).map(([key,value])=><p key={key}>{key==="home"?"Home win":key==="away"?"Away win":"Draw"}<strong>{percent(value)}</strong></p>)}</div> : <p>Not a home win · {percent(result.probabilities.not_home_win)}</p>}<p>History: {result.history.home_games.toLocaleString()} home-team games · {result.history.away_games.toLocaleString()} away-team games</p>{replay&&<div className={`replay-verdict ${result.correct?"correct":"incorrect"}`}><strong>{result.correct?"Prediction matched the result":"Prediction missed the result"}</strong><p>Final score {result.home_score} – {result.away_score} · Trained on {result.training_games?.toLocaleString()} earlier matches</p><p>Training ends {result.training_end?.slice(0,10)} · Target result excluded</p></div>}<p className="prediction-note">{distribution ? "These outcome probabilities also generate the market prices. Estimates, never guarantees." : "Binary historical baseline: home win vs not-home-win, including EPL draws. Estimates, never guarantees."}</p></div>}</section>;
}
