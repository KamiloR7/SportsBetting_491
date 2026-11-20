import BetSlip from "./BetSlip";
import TeamBadge from "./TeamBadge";
import { matchTeamStyle } from "../services/teamBranding";
import { Link } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { apiRequest } from "../services/api";

function TeamIdentity({ name, side, match }) {
  return <span className="team-identity"><TeamBadge name={name} logoUrl={match[`${side}_logo_url`]} primaryColor={match[`${side}_primary_color`]} secondaryColor={match[`${side}_secondary_color`]} className={`badge-${side}`}/><span className="team-copy"><small>{side.toUpperCase()}</small><strong>{name}</strong></span></span>;
}
export default function MatchCard(props) {
  // A reused card must not offer a previous match's odds or inline selection.
  return <MatchCardContent key={`${props.match.id}:${props.match.status}:${props.match.start_time}`} {...props} />;
}

function MatchCardContent({ match, returnParams }) {
  const quickSlip = useRef(null);
  const quickSlipTrigger = useRef(null);
  const [submitting, setSubmitting] = useState(false);
  const [quickPick, setQuickPick] = useState(null);
  useEffect(() => {
    if (quickPick && quickSlip.current) {
      quickSlip.current.focus({ preventScroll: true });
      quickSlip.current.scrollIntoView({ block: "nearest", behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth" });
      return;
    }

    if (!quickPick && quickSlipTrigger.current) {
      quickSlipTrigger.current.focus({ preventScroll: true });
      quickSlipTrigger.current = null;
    }
  }, [quickPick]);
  const openQuickSlip = (selection, event) => {
    quickSlipTrigger.current = event.currentTarget;
    setQuickPick(selection);
  };
  const [market, setMarket] = useState(null);
  const [loading, setLoading] = useState(match.status === "scheduled" || match.status === "in_progress");
  const final = match.status === "final";
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 30000); return () => clearInterval(timer); }, []);
  useEffect(() => {
    if (final || !["scheduled", "in_progress"].includes(match.status)) return;
    const controller = new AbortController();
    apiRequest(`/matches/${match.id}/markets`, { signal: controller.signal })
      .then(markets => { if (!controller.signal.aborted) setMarket(markets.find(item => ["model_derived", "model_reconstructed"].includes(item.odds_source)) || null); })
      .catch(() => {})
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [match.id, match.status, final]);
  const date = new Date(match.start_time);
  const started = match.status === "in_progress" || Date.parse(match.start_time) <= now;
  const outcomes = ["home", "draw", "away"].map(selection => market?.outcomes.find(o => o.selection === selection)).filter(Boolean);
  const canPick = match.status === "scheduled" && !started && market?.is_open && market.odds_source === "model_derived" && outcomes.length > 0;
  const teamRow = side => {
    const name = match[`${side}_team_name`];
    const available = canPick && outcomes.some(o => o.selection === side);
    return <div className="fixture-team">{available ? <button type="button" className="team-pick-button" disabled={submitting} aria-expanded={quickPick === side} onClick={event => openQuickSlip(side, event)}><TeamIdentity name={name} side={side} match={match}/><span className="team-pick-hint">Pick →</span></button> : <TeamIdentity name={name} side={side} match={match}/ >}{final && <strong>{match[`${side}_score`] ?? "—"}</strong>}</div>;
  };
  return <article className={`match-card fixture-card sport-${returnParams.get("league")} ${final ? "fixture-finished" : "fixture-open"}`} style={matchTeamStyle(match)}>
    <div className="fixture-card-top"><time dateTime={match.start_time}>{date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}</time><span className={`status-chip ${match.status}`}>{final ? "Final" : started && match.status === "scheduled" ? "Started · awaiting update" : match.status === "in_progress" ? "In progress · betting closed" : match.status.replaceAll("_", " ")}</span></div>
    <h4 className="sr-only">{match.home_team_name} vs {match.away_team_name}</h4>
    {teamRow("home")}
    {teamRow("away")}
    {!final && <div className="browse-market"><p>{loading ? "Loading model odds…" : market ? (market.odds_source === "model_reconstructed" ? "Reconstructed pregame model odds" : started || !market.is_open ? "Last pregame odds · betting closed" : "Model odds · match winner") : started ? "No pregame estimate available" : "Model odds unavailable"}</p>{outcomes.length > 0 && <div className="browse-odds">{outcomes.map(o => canPick ? <button type="button" className={`odds-${o.selection} board-odds-pick`} disabled={submitting} key={o.id ?? o.selection} aria-pressed={quickPick === o.selection} onClick={event => openQuickSlip(o.selection, event)}><small>{o.selection === "home" ? match.home_team_name : o.selection === "away" ? match.away_team_name : "Draw"}</small><strong>{Number(o.decimal_odds).toFixed(2)}</strong><span>Bet / Parlay +</span></button> : <span className={`odds-${o.selection}`} key={o.id ?? o.selection}><small>{o.selection === "home" ? "Home" : o.selection === "away" ? "Away" : "Draw"}</small><strong>{Number(o.decimal_odds).toFixed(2)}</strong></span>)}</div>}{market?.odds_source === "model_reconstructed" && <small>Prior-day data only · not live odds · betting closed.</small>}{match.status === "in_progress" && <small>Open match center for the latest stored score.</small>}</div>}
    {canPick ? <div className="board-bet-actions"><button type="button" className="board-bet-now" disabled={submitting} aria-expanded={quickPick !== null} onClick={event => openQuickSlip(quickPick || outcomes[0].selection, event)}>Place a bet <span aria-hidden="true">→</span></button><Link to={`/matches/${match.id}?${returnParams}`}>Model insights & match details ↗</Link></div> : <Link className="match-card-action" to={`/matches/${match.id}?${returnParams}`}>{final ? "View result & replay" : "View match & prediction"}<span aria-hidden="true">↗</span></Link>}
    {canPick && quickPick && <div className="board-quick-slip" ref={quickSlip} role="region" tabIndex={-1} aria-label="Bet slip for this match"><div className="quick-slip-heading"><strong>Your match pick</strong><button type="button" disabled={submitting} onClick={() => setQuickPick(null)} aria-label="Close bet slip">Close ×</button></div><BetSlip key={`${match.id}-${quickPick}`} match={match} initialSelection={quickPick} onBusyChange={setSubmitting}/></div>}
  </article>;
}
