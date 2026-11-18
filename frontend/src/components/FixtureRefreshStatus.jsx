import { useEffect, useState } from "react";
import { apiRequest } from "../services/api";
export default function FixtureRefreshStatus({ compact = false }) {
  const [status, setStatus] = useState(null);
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    async function check() {
      try { const data = await apiRequest("/health", { signal: controller.signal }); if (active) setStatus({ ...data.fixture_refresh, observed_at: Date.now() }); }
      catch { if (active) setStatus(previous => ({ ...previous, state: "error", unreachable: true })); }
    }
    check(); const timer = setInterval(check, 30000);
    return () => { active = false; controller.abort(); clearInterval(timer); };
  }, []);
  if (!status) return <p className={`refresh-status ${compact ? "refresh-compact" : ""}`} role="status">Checking fixture updates…</p>;
  const last = status.last_success ? new Date(status.last_success) : null;
  const delayed = status.state === "error" || (last && status.observed_at - last.getTime() > Math.max(300000, (status.interval_seconds || 120) * 3000));
  return <div className={`refresh-status ${compact ? "refresh-compact" : ""} ${delayed ? "refresh-delayed" : ""}`} role="status"><span className="refresh-dot"/><span><strong>{delayed ? "Updates delayed" : status.enabled ? `Auto updates · every ${Math.round(status.interval_seconds / 60)} min` : "Automatic updates off"}</strong><small>{last ? `Last successful refresh ${last.toLocaleTimeString([], { hour: "numeric", minute: "2-digit", second: "2-digit" })}` : status.unreachable ? "Cannot reach the server; stored games may be out of date." : status.enabled ? "Fetching the latest provider results…" : "Showing stored fixtures."} · {status.source || "Provider"} data may lag.</small></span></div>;
}
