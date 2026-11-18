export function safeTeamColor(value, fallback = "#64748b") {
  return /^#[0-9a-f]{6}$/i.test(value || "") ? value : fallback;
}
function rgb(value) {
  const color = safeTeamColor(value);
  return [1, 3, 5].map(start => parseInt(color.slice(start, start + 2), 16)).join(" ");
}
function isLight(value) {
  const parts=rgb(value).split(" ").map(Number);
  return (parts[0]*0.2126+parts[1]*0.7152+parts[2]*0.0722)/255 > 0.7;
}
export function matchTeamStyle(match) {
  return { "--home-color": safeTeamColor(match.home_primary_color), "--away-color": safeTeamColor(match.away_primary_color),
    "--home-rgb": rgb(match.home_primary_color), "--away-rgb": rgb(match.away_primary_color),
    "--home-glow": isLight(match.home_primary_color) ? 0.25 : 0.65, "--away-glow": isLight(match.away_primary_color) ? 0.18 : 0.42,
    "--home-odds-alpha": isLight(match.home_primary_color) ? 0.14 : 0.48, "--away-odds-alpha": isLight(match.away_primary_color) ? 0.14 : 0.48 };
}
