import { useState } from "react";
import { safeTeamColor } from "../services/teamBranding";
export default function TeamBadge({ name, logoUrl, primaryColor, secondaryColor, className = "" }) {
  const [failedLogo, setFailedLogo] = useState(null);
  const verifiedUrl = /^https:\/\/a\.espncdn\.com\/i\/teamlogos\//.test(logoUrl || "");
  const showLogo = verifiedUrl && failedLogo !== logoUrl;
  const initials = (name || "Team").split(" ").filter(Boolean).map(word => word[0]).slice(0, 3).join("");
  return <span className={`team-badge ${className} ${showLogo ? "has-logo" : ""}`} style={{ "--badge-primary": safeTeamColor(primaryColor), "--badge-secondary": safeTeamColor(secondaryColor, safeTeamColor(primaryColor)) }} aria-hidden="true">{showLogo ? <img src={logoUrl} alt="" loading="lazy" decoding="async" referrerPolicy="no-referrer" onError={() => setFailedLogo(logoUrl)} /> : initials}</span>;
}
