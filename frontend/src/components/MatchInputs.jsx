import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiRequest } from "../services/api";

export default function MatchInputs({ matchId }) {
  const [state, setState] = useState({ loading: true });
  useEffect(() => {
    const controller = new AbortController();
    apiRequest(`/insights/matches/${matchId}/inputs`, { signal: controller.signal })
      .then(data => setState({ data }))
      .catch(error => { if (!controller.signal.aborted) setState({ error: error.message }); });
    return () => controller.abort();
  }, [matchId]);
  const data = state.data;
  const stats = [{ key: "win_rate", label: "Prior win rate", format: x => `${(x * 100).toFixed(1)}%` }, { key: "avg_score", label: `Average ${data?.units || "score"} scored`, format: x => x.toFixed(2) }, { key: "avg_allowed", label: `Average ${data?.units || "score"} allowed`, format: x => x.toFixed(2) }];
  return <section className="match-inputs ml-analysis-card" aria-labelledby="match-inputs-heading"><div className="ml-section-heading"><div><span className="section-kicker">THE SIX MODEL INPUTS</span><h2 id="match-inputs-heading">What went into this matchup?</h2></div><Link to="/insights#ml-evaluation">See model evaluation ↗</Link></div>
    {state.loading && <p role="status">Building prior-day team statistics…</p>}{state.error && <p role="status">Input breakdown unavailable: {state.error}</p>}
    {data && <><p>Three statistics for each team, before this game’s UTC date. These are actual feature values, not estimates of which input caused the prediction.</p><div className="ml-table-scroll"><table className="match-input-table"><caption>Prior-day feature comparison · {data.sport}</caption><thead><tr><th scope="col">Model input</th>{data.teams.map(team => <th key={team.side} scope="col"><small>{team.side.toUpperCase()}</small>{team.name}</th>)}</tr></thead><tbody>{stats.map(stat => <tr key={stat.key}><th scope="row">{stat.label}</th>{data.teams.map(team => <td key={team.side}>{stat.format(team[stat.key])}</td>)}</tr>)}<tr className="ml-history-row"><th scope="row">Earlier completed games<small>History size; not an extra model input</small></th>{data.teams.map(team => <td key={team.side}>{team.history_games.toLocaleString()}</td>)}</tr></tbody></table></div><p className="ml-report-note">Cutoff: {new Date(data.feature_cutoff).toISOString().replace("T", " ").replace(".000Z", " UTC")} · All available prior-day history; not just recent form. A draw counts as a non-win in win rate.</p>{data.model && <p className="ml-model-context">Configured model: <code>{data.model.version}</code>{!data.model.eligible_for_target && <span> · Trained after this target’s cutoff; these inputs do not make that model valid for this historical match. Use the separately trained historical replay.</span>}</p>}{!data.model && <p className="fine-print">Configured market-model information is unavailable; this table shows historical inputs only.</p>}<p className="fine-print">Reconstructed now from stored completed results using the same history builder as match forecasts. This is not a recorded pregame snapshot; later data corrections can change it. Target-game scores, same-day results, injuries, weather and lineups are excluded.</p></>}
  </section>;
}
