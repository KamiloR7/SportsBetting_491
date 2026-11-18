import { useRef, useState } from "react";
import { mutation } from "../services/api";
import { saveParlayDraft, clearPendingParlay } from "../services/parlayDraft";
export default function ResetDemoForm() {
  const [open, setOpen] = useState(false), [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false), [message, setMessage] = useState("");
  const request = useRef(null);
  async function reset(e) {
    e.preventDefault(); if (!confirmed || busy) return;
    setBusy(true); setMessage("");
    request.current ||= { request_key: crypto.randomUUID(), confirmation: "RESET" };
    try {
      const result = await mutation("/wallet/demo-reset", request.current);
      request.current = null; saveParlayDraft([]); clearPendingParlay();
      window.dispatchEvent(new Event("wallet-updated"));
      setMessage(`Demo reset complete. Balance: ${result.balance.toLocaleString()} points. Your bets and previous activity have been cleared.`);
      setOpen(false); setConfirmed(false);
    } catch (e) { setMessage(e.message); if (e.status >= 400 && e.status < 500) request.current = null; }
    finally { setBusy(false); }
  }
  return <section className="explainer-card reset-demo"><span className="section-kicker">A FRESH ROUND</span><h2>Start over, anytime.</h2><p>Restore 1,000 virtual points and clear your single bets, parlays and wallet activity. This includes pending bets: they will no longer settle or pay out. Your account stays signed in.</p>{!open ? <button className="secondary-button" onClick={() => { setOpen(true); setMessage(""); }}>Reset demo wallet & bets</button> : <form onSubmit={reset}><label className="reset-confirm"><input type="checkbox" checked={confirmed} disabled={busy} onChange={e => setConfirmed(e.target.checked)} />I understand this permanently clears my bets and activity.</label><div className="reset-actions"><button disabled={!confirmed || busy}>{busy ? "Resetting…" : "Confirm reset to 1,000 points"}</button><button type="button" disabled={busy} onClick={() => { setOpen(false); setConfirmed(false); }}>Keep my bets</button></div></form>}{message && <p role="status">{message}</p>}</section>;
}
