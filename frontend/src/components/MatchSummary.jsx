function MatchSummary({ match }) {
  const startTime = new Date(match.start_time);
  const dateTime = Number.isNaN(startTime.getTime())
    ? "Date and time unavailable"
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
