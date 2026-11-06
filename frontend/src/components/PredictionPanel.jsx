import { useEffect, useRef, useState } from "react";
import { createPrediction } from "../services/predictions";
import { predictionDisplay } from "../services/predictionTransparency";

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
    setState({ loading: true, result: null, error: "" });
    createPrediction(matchId, { signal: controller.signal })
      .then((result) => {
        if (!controller.signal.aborted) setState({ loading: false, result: { ...result, display: predictionDisplay(result) }, error: "" });
      })
      .catch((error) => {
        if (!controller.signal.aborted) {
          setState({ loading: false, result: null, error: error.message });
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
      {state.result && (
        <div className="prediction-result" aria-live="polite">
          <p><strong>{state.result.display.headline}</strong></p>
          <p>Confidence: {percent(state.result.display.confidence)}</p>
          {state.result.display.probabilities.map(({ key, label, value }) => (
            <p key={key}>{label}: {percent(value)}</p>
          ))}
          {state.result.history && <p>History used: {state.result.history.home_games} home-team games and {state.result.history.away_games} away-team games</p>}
          <p className="prediction-note">{state.result.display.message}</p>
          <p className="prediction-note">{state.result.display.calibrationNote}</p>
        </div>
      )}
    </section>
  );
}

export default PredictionPanel;
