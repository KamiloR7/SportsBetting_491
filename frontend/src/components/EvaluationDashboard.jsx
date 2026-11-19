import { useEffect, useState } from "react";
import { apiRequest } from "../services/api";

const label = value => ({ home_win: "Home win", away_win: "Away win", draw: "Draw" }[value] || value);
const pct = value => `${(value * 100).toFixed(1)}%`;
const day = value => value?.slice(0, 10) || "Unavailable";

export default function EvaluationDashboard() {
  const [state, setState] = useState({ loading: true });
  const [sport, setSport] = useState("NFL");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    apiRequest("/insights/audit", { signal: controller.signal })
      .then(data => setState({ data }))
      .catch(error => { if (!controller.signal.aborted) setState({ error: error.message }); });
    return () => controller.abort();
  }, [attempt]);
  const data = state.data;
  const current = data?.sports.find(item => item.sport === sport) || data?.sports[0];
  const neverPicked = current?.classes.filter((_, column) => current.confusion_matrix.every(row => row[column] === 0)) || [];
  return <section className="ml-evaluation" id="ml-evaluation" aria-labelledby="evaluation-heading">
    <div className="ml-section-heading"><div><span className="section-kicker">MEASURE THE MODEL</span><h2 id="evaluation-heading">Evidence behind the accuracy.</h2></div><span className="outline-pill">VERIFIED HOLDOUT</span></div>
    <p>Earlier games train the model. Later games test it. These results reproduce the saved model snapshot; they are separate from your betting record.</p>
    {state.loading && <p role="status">Loading verified evaluation…</p>}
    {state.error && <div className="ml-unavailable" role="status"><p>{state.error}</p><p>No replacement scores or demonstration metrics are shown.</p><button type="button" onClick={() => { setState({ loading: true }); setAttempt(attempt + 1); }}>Try again</button></div>}
    {data && <>
      <div className="ml-sport-tabs" role="group" aria-label="Evaluation sport">{data.sports.map(item => <button key={item.sport} type="button" aria-pressed={current?.sport === item.sport} onClick={() => setSport(item.sport)}>{item.sport}<small>{item.classes.length}-outcome winner</small></button>)}</div>
      {data.unavailable.map(item => <p className="ml-unavailable" key={item.sport}>{item.sport}: {item.reason}</p>)}
      {current && <>
        <div className="ml-metric-grid">
          <article><span>Held-out accuracy</span><strong>{pct(current.accuracy)}</strong><small>{current.correct.toLocaleString()} correct / {current.test_rows.toLocaleString()} games</small></article>
          <article><span>Majority baseline</span><strong>{pct(current.baseline_accuracy)}</strong><small>Always predict {label(current.baseline_outcome).toLowerCase()}, selected from training</small></article>
          <article><span>Difference from baseline</span><strong className={current.accuracy >= current.baseline_accuracy ? "ml-positive" : "ml-caution"}>{current.accuracy >= current.baseline_accuracy ? "+" : ""}{((current.accuracy - current.baseline_accuracy) * 100).toFixed(1)}<em> pp</em></strong><small>Percentage points; one historical holdout</small></article>
        </div>
        <div className="ml-evidence-strip"><div><span>Train · {current.train_rows.toLocaleString()} games</span><strong>{day(current.train_start)} → {day(current.train_end)}</strong></div><div><span>Test · {current.test_rows.toLocaleString()} games</span><strong>{day(current.test_start)} → {day(current.test_end)}</strong></div><div><span>Model snapshot</span><strong className="ml-version">{current.model_version}</strong></div></div>
        <div className="ml-analysis-grid">
          <section className="ml-analysis-card"><span className="section-kicker">WHERE IT MISSES</span><h3>Predicted versus actual.</h3><p>Rows show the real result. Columns show the model’s pick. The diagonal contains correct predictions.</p><div className="ml-table-scroll"><table className="confusion-table"><caption>{current.sport} held-out confusion matrix — counts of games</caption><thead><tr><th scope="col">Actual ↓ / Predicted →</th>{current.classes.map(name => <th scope="col" key={name}>{label(name)}</th>)}</tr></thead><tbody>{current.confusion_matrix.map((row, i) => <tr key={current.classes[i]}><th scope="row">{label(current.classes[i])}</th>{row.map((count, j) => <td key={current.classes[j]} className={i === j ? "ml-correct-cell" : "ml-missed-cell"}><strong>{count}</strong><small>{row.reduce((a, b) => a + b, 0) ? pct(count / row.reduce((a, b) => a + b, 0)) : "—"} of row</small></td>)}</tr>)}</tbody></table></div>{neverPicked.length > 0 && <p className="ml-unavailable">No leading predictions for {neverPicked.map(label).join(", ").toLowerCase()} in this holdout. The model can assign an outcome probability without ever ranking it first.</p>}<p className="fine-print">Log loss: <b>{current.log_loss.toFixed(3)}</b>. This scores the full probability distribution; lower is better. Accuracy only scores the leading pick.</p></section>
          <section className="ml-analysis-card"><span className="section-kicker">PROBABILITY RELIABILITY</span><h3>Does confidence match results?</h3><p>For each game, take the highest predicted probability. Group those leading picks into 10-point bands, then compare average confidence with the fraction correct.</p><div className="ml-calibration-legend"><span>● Model confidence</span><span>● Actually correct</span></div><div className="ml-calibration-bins">{current.calibration_bins.filter(bin => bin.count).map(bin => <div className="ml-calibration-row" key={bin.lower}><div className="ml-bin-label"><strong>{Math.round(bin.lower * 100)}–{Math.round(bin.upper * 100)}%</strong><small>{bin.count} {bin.count === 1 ? "game" : "games"}{bin.count < 30 ? " · small sample" : ""}</small></div><div className="ml-bin-bars"><div><span style={{ width: pct(bin.mean_confidence) }}/><b>{pct(bin.mean_confidence)}</b></div><div><span style={{ width: pct(bin.accuracy) }}/><b>{pct(bin.accuracy)}</b></div></div></div>)}</div><p className="fine-print">Weighted absolute gap across these bins: <b>{(current.expected_calibration_error * 100).toFixed(1)} percentage points</b>. Bins are lower-inclusive, upper-exclusive (100% included in the last). Empty bins are omitted. Small samples are noisy; this does not prove the model is calibrated.</p></section>
        </div>
        <details className="ml-method"><summary>How was this evaluated without result leakage?</summary><ol><li>Build each team’s cumulative win rate, average scored and average allowed using completed games on earlier UTC dates. No same-day or target-game scores enter its features.</li><li>Split on whole dates near 80% training / 20% testing. Fit StandardScaler and logistic regression only on the earlier training partition; keep that fit fixed throughout the test.</li><li>Earlier held-out results may update the history for later held-out games, as they would become available over time. They never refit the evaluation model.</li><li>Compare the model against always picking the most common training outcome. NFL/MLB ties are excluded from the winner target; EPL draws are a separate class. Cold-start training rows use zero history values.</li><li>Verify the source-data fingerprint and accuracy against the saved snapshot. The deployed model is a separate refit on all eligible snapshot history; its version identifies the snapshot, not the training-only evaluation fit.</li></ol><p>{current.model_type}. No injuries, weather, lineups or player statistics. A single chronological holdout is not a guarantee of future accuracy or profitable betting.</p><code>Dataset SHA-256: {current.dataset_sha256}</code></details>
      </>}
      <p className="ml-report-note">Model snapshot: {day(data.source_generated_at)} · Audit reproduced: {new Date(data.generated_at).toLocaleString()} local time · Training uses results before {day(data.data_cutoff)} UTC. This report stays tied to that snapshot; automatic fixture refresh does not retrain it.</p>
    </>}
  </section>;
}
