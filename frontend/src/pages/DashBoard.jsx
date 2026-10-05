import { useEffect, useState } from "react";
import MatchCard from "../components/MatchCard";
import { getLeagues, getMatches } from "../services/matches";

const LEAGUES = ["NBA", "NFL", "EPL"];

function LeagueMatches({ abbreviation }) {
  const [result, setResult] = useState({ loading: true, matches: [], error: "" });

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const options = { signal: controller.signal };
        const leagues = await getLeagues(options);
        const league = leagues.find((item) => item.abbreviation === abbreviation);
        if (!league) throw new Error(`${abbreviation} is currently unavailable.`);
        const matches = await getMatches(league.id, options);
        if (!controller.signal.aborted) setResult({ loading: false, matches, error: "" });
      } catch (error) {
        if (!controller.signal.aborted) setResult({ loading: false, matches: [], error: error.message });
      }
    }
    load();
    return () => controller.abort();
  }, [abbreviation]);

  if (result.loading) return <p role="status">Loading {abbreviation} matches…</p>;
  if (result.error) return <p role="alert">{result.error}</p>;
  if (!result.matches.length) return <p role="status">No {abbreviation} matches are available.</p>;

  return (
    <div className="match-grid">
      {result.matches.map((match) => <MatchCard key={match.id} match={match} />)}
    </div>
  );
}

function Dashboard() {
  const [selectedLeague, setSelectedLeague] = useState("NBA");

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Matches</h1>
        <p>Select a league to browse matches.</p>
      </header>
      <div className="sport-buttons" role="group" aria-label="League selection">
        {LEAGUES.map((league) => (
          <button key={league} aria-pressed={selectedLeague === league} onClick={() => setSelectedLeague(league)}>
            {league}
          </button>
        ))}
      </div>
      <LeagueMatches key={selectedLeague} abbreviation={selectedLeague} />
    </div>
  );
}

export default Dashboard;
