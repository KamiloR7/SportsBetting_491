import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { apiRequest } from "../services/api";

export default function MatchCard({ match, returnParams }) {
  const [market, setMarket] = useState(null);
  const [loading, setLoading] = useState(match.status === "scheduled" || match.status === "in_progress");
  const final = match.status === "final";
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 30000); return () => clearInterval(timer); }, []);
  useEffect(() => {
    if (final || !["scheduled", "in_progress"].includes(match.status)) return;
    const controller = new AbortController();
    apiRequest(`/matches/${match.id}/markets`, { signal: controller.signal })
      .then(markets => setMarket(markets.find(item => ["model_derived", "model_reconstructed"].includes(item.odds_source)) || null))
      .catch(() => {})
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [match.id, match.status, final]);
  const date = new Date(match.start_time);
  const started = match.status === "in_progress" || Date.parse(match.start_time) <= now;
  const outcomes = ["home", "draw", "away"].map(selection => market?.outcomes.find(o => o.selection === selection)).filter(Boolean);
  return <article className={`match-card fixture-card sport-${returnParams.get("league")}`}>
    <div className="fixture-card-top"><time dateTime={match.start_time}>{date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}</time><span className={`status-chip ${match.status}`}>{final ? "Final" : started && match.status === "scheduled" ? "Started · awaiting update" : match.status === "in_progress" ? "In progress · betting closed" : match.status.replaceAll("_", " ")}</span></div>
    <h4 className="sr-only">{match.home_team_name} vs {match.away_team_name}</h4>
    <div className="fixture-team"><span><small>HOME</small>{match.home_team_name}</span>{final && <strong>{match.home_score ?? "—"}</strong>}</div>
    <div className="fixture-team"><span><small>AWAY</small>{match.away_team_name}</span>{final && <strong>{match.away_score ?? "—"}</strong>}</div>
    {!final && <div className="browse-market"><p>{loading ? "Loading model odds…" : market ? (market.odds_source === "model_reconstructed" ? "Reconstructed pregame model odds" : started || !market.is_open ? "Last pregame odds · betting closed" : "Model odds · match winner") : started ? "No pregame estimate available" : "Model odds unavailable"}</p>{outcomes.length > 0 && <div className="browse-odds">{outcomes.map(o => <span key={o.id ?? o.selection}><small>{o.selection === "home" ? "Home" : o.selection === "away" ? "Away" : "Draw"}</small><strong>{Number(o.decimal_odds).toFixed(2)}</strong></span>)}</div>}{market?.odds_source === "model_reconstructed" && <small>Prior-day data only · not live odds · betting closed.</small>}{match.status === "in_progress" && <small>Open match center for the latest stored score.</small>}</div>}
    <Link className="match-card-action" to={`/matches/${match.id}?${returnParams}`}>{final ? "View result & replay" : "View prediction & picks"}<span aria-hidden="true">↗</span></Link>
  </article>;
}
