import { useState } from "react";
function summary(ticket) {
  const parlay = ticket.type === "parlay";
  const lines = ["VIGOR · Virtual points only · No cash value", parlay ? `${ticket.legs.length}-leg parlay` : `${ticket.home_team_name || "Home"} vs ${ticket.away_team_name || "Away"}`];
  if (parlay) ticket.legs.forEach((leg, i) => lines.push(`${i + 1}. ${leg.home_team_name} vs ${leg.away_team_name}: ${leg.selection === "draw" ? "Draw" : leg.selection === "home" ? leg.home_team_name : leg.away_team_name} @ ${Number(leg.accepted_odds).toFixed(2)} · ${leg.status}`));
  else lines.push(`Pick: ${ticket.selection === "draw" ? "Draw" : ticket.selection === "home" ? ticket.home_team_name || "Home" : ticket.away_team_name || "Away"}`);
  lines.push(`Stake: ${ticket.stake} points`, `${parlay ? "Combined" : "Accepted"} odds: ${Number(parlay ? ticket.combined_odds : ticket.accepted_odds).toFixed(parlay ? 4 : 2)}`, `Original potential return: ${ticket.potential_payout} points (includes stake)`, `Status: ${ticket.status}`);
  if (ticket.status !== "PENDING") lines.push(`Actual return: ${parlay ? ticket.actual_payout ?? 0 : ticket.status === "WON" ? ticket.potential_payout : ticket.status === "VOID" ? ticket.stake : 0} points`);
  else if (parlay && ticket.current_potential_payout !== ticket.potential_payout) lines.push(`Current potential return after voids: ${ticket.current_potential_payout} points`);
  return lines.join("\n");
}
export default function ShareTicket({ ticket }) {
  const [message, setMessage] = useState(""), [manual, setManual] = useState(false);
  const text = summary(ticket);
  async function copy() {
    try { await navigator.clipboard.writeText(text); setMessage("Bet summary copied. Paste it into a message to share."); setManual(false); }
    catch { setManual(true); setMessage("Copy the summary below to share your bet."); }
  }
  return <div className="ticket-sharing"><button className="secondary-button" type="button" onClick={copy}>Share {ticket.type === "parlay" ? "parlay" : "bet"} ↗</button>{message && <p role="status">{message}</p>}{manual && <textarea aria-label="Bet summary to share" readOnly value={text} rows={8} onFocus={e => e.target.select()} />}</div>;
}
