import { useState } from "react";

import MatchCard from "../components/MatchCard";
import mockMatches from "../data/testMatches";

function Dashboard() {
  const [selectedLeague, setSelectedLeague] =
    useState("All");

  const filteredMatches =
    selectedLeague === "All"
      ? mockMatches
      : mockMatches.filter(
          (match) =>
            match.league === selectedLeague
        );

  return (
    <div className="dashboard">

      <header className="dashboard-header">

        <h1>Today's Matches</h1>

        <p>
          Select a match to view predictions
        </p>

      </header>

      <div className="sport-buttons">

        <button
          onClick={() =>
            setSelectedLeague("All")
          }
        >
          All
        </button>

        <button
          onClick={() =>
            setSelectedLeague("NBA")
          }
        >
          NBA
        </button>

        <button
          onClick={() =>
            setSelectedLeague("NFL")
          }
        >
          NFL
        </button>

        <button
          onClick={() =>
            setSelectedLeague(
              "Premier League"
            )
          }
        >
          Premier League
        </button>

      </div>

      <div className="match-grid">

        {filteredMatches.map((match) => (
          <MatchCard
            key={match.id}
            match={match}
          />
        ))}

      </div>

    </div>
  );
}

export default Dashboard;