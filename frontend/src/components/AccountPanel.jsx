import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { apiRequest, mutation } from "../services/api";
import DemoPointsForm from "./DemoPointsForm";

export default function AccountPanel() {
  const location = useLocation();
  const accountRef = useRef(null);
  const [state, setState] = useState({ loading: true });
  const [adding, setAdding] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const refresh = useCallback(async () => {
    try {
      const user = await apiRequest("/auth/me");
      const wallet = await apiRequest("/wallet");
      setState({ user, wallet });
    } catch (e) { setState({ error: e.message, status: e.status }); }
  }, []);
  useEffect(() => {
    let active = true;
    Promise.resolve().then(() => { if (active) { setAdding(false); refresh(); } });
    const update = () => refresh();
    window.addEventListener("wallet-updated", update);
    const timer = setInterval(update, 30000);
    return () => { active = false; clearInterval(timer); window.removeEventListener("wallet-updated", update); };
  }, [refresh, location.pathname]);
  useEffect(() => {
    if (!adding) return;
    const outside = event => { if (!accountRef.current?.contains(event.target)) setAdding(false); };
    const escape = event => { if (event.key === "Escape") setAdding(false); };
    document.addEventListener("pointerdown", outside);
    document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("pointerdown", outside); document.removeEventListener("keydown", escape); };
  }, [adding]);
  async function signOut() {
    if (signingOut) return;
    setSigningOut(true);
    try {
      await mutation("/auth/logout", {});
      setAdding(false);
      window.dispatchEvent(new Event("wallet-updated"));
      await refresh();
    } catch (e) { setState(previous => ({ ...previous, error: e.message })); }
    finally { setSigningOut(false); }
  }
  if (state.loading) return <div className="header-account"><span role="status">Loading account…</span></div>;
  if (!state.user) return <div className="header-account header-guest"><span>Virtual points only</span><Link className="header-join" to="/login">Sign in / Join ↗</Link>{state.status !== 401 && state.error && <small role="alert">{state.error}</small>}</div>;
  return <section className="header-account" aria-label="Your account" ref={accountRef}>
    <Link className="header-balance" to="/wallet" title={`Wallet for ${state.user.email}`}><strong>{state.wallet.balance.toLocaleString()}</strong><span>PTS ↗<small>No cash value</small></span></Link>
    <button className="header-topup" type="button" aria-expanded={adding} aria-controls="header-demo-points" onClick={() => setAdding(!adding)}>{adding ? "Close ×" : "+ Demo points"}</button>
    <button type="button" disabled={signingOut} onClick={signOut}>{signingOut ? "Signing out…" : "Sign out"}</button>
    {adding && <div className="header-topup-panel" id="header-demo-points" role="region" aria-label="Add demo points"><strong>Add virtual points</strong><p className="header-account-email">{state.user.email}</p><DemoPointsForm/></div>}
    {state.error && <p className="header-account-error" role="alert">{state.error}</p>}
  </section>;
}
