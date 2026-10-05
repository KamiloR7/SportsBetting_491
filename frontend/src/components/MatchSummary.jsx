function MatchSummary({ match }) {
  const hasStartTime = match.start_time != null &&
    !(typeof match.start_time === "string" && match.start_time.trim() === "");
  const startTime = hasStartTime ? new Date(match.start_time) : null;
  const dateTime = !startTime || Number.isNaN(startTime.getTime())
    ? "Date/time unavailable"
    : startTime.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
  const status = match.status
    ? match.status.replaceAll("_", " ")
    : "Unavailable";

  return (
    <>
      <p className="league-name">{match.league_name || "League unavailable"}</p>
      <h2>{match.home_team_name || "Home team unavailable"} vs {match.away_team_name || "Away team unavailable"}</h2>
      <p>{dateTime}</p>
      <p>Status: {status}</p>
      {(match.home_score != null || match.away_score != null) && (
        <p>Score (home–away): {match.home_score ?? "—"} – {match.away_score ?? "—"}</p>
      )}
    </>
  );
}

export default MatchSummary;
