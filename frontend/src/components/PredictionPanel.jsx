import { useEffect, useRef, useState } from "react";
import { createPrediction } from "../services/predictions";
import { savePredictionToHistory } from "../services/predictionHistory";

function percent(value) {
  return `${Math.round(value * 100)}%`;
}

function PredictionPanel({ matchId }) {
  const [state, setState] = useState({ loading: false, result: null, error: "" });
  const controllerRef = useRef(null);

  useEffect(() => () => controllerRef.current?.abort(), []);

  function handleGenerate() {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setState({ loading: true, result: null, error: "", historyWarning: "" });
    createPrediction(matchId, { signal: controller.signal })
      .then((result) => {
        if (!controller.signal.aborted) {
          const saved = savePredictionToHistory(result);
          setState({
            loading: false,
            result,
            error: "",
            historyWarning: saved
              ? ""
              : "Prediction generated, but browser storage is unavailable; it was not added to prediction history.",
          });
        }
      })
      .catch((error) => {
        if (!controller.signal.aborted) {
          setState({ loading: false, result: null, error: error.message, historyWarning: "" });
        }
      });
  }

  return (
    <section className="prediction-panel" aria-labelledby="prediction-heading">
      <h2 id="prediction-heading">Match prediction</h2>
      <p>Generate a prediction using this matchup’s prior team history.</p>
      <button type="button" disabled={state.loading} onClick={handleGenerate}>
        {state.loading ? "Generating…" : "Generate prediction"}
      </button>
      {state.loading && <p role="status">Loading prediction…</p>}
      {state.error && <p role="alert">{state.error}</p>}
      {state.historyWarning && <p role="status">{state.historyWarning}</p>}
      {state.result && (
        <div className="prediction-result" aria-live="polite">
          <p><strong>Predicted outcome: {state.result.predicted_outcome === "HOME_WIN"
            ? "Home win"
            : "Not a home win"}</strong></p>
          <p>{state.result.home_team_name} vs {state.result.away_team_name} ({state.result.sport})</p>
          <p>Confidence: {percent(state.result.confidence)}</p>
          <p>Home win: {percent(state.result.probabilities.home_win)}</p>
          <p>Not home win: {percent(state.result.probabilities.not_home_win)}</p>
          <p>History used: {state.result.history.home_games} home-team games and {state.result.history.away_games} away-team games</p>
          <p className="prediction-note">NFL, MLB, and EPL currently use a binary home-win versus not-home-win model.</p>
        </div>
      )}
    </section>
  );
}

export default PredictionPanel;
