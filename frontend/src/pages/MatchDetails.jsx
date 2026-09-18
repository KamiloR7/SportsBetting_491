import { useParams } from "react-router-dom";
import { useState } from "react";

import mockMatches from "../data/testMatches";
import BettingOptions from "../components/BettingOptions";

function MatchDetails() {
  const { id } = useParams();

  const [selectedBet, setSelectedBet] =
    useState(null);

  const match = mockMatches.find(
    (match) =>
      match.id === Number(id)
  );

  if (!match) {
    return <h2>Match not found</h2>;
  }

  function handleSelectBet(bet) {
    setSelectedBet(bet);
  }

  return (
    <div className="match-details">

      <p>{match.league}</p>

      <h1>
        {match.homeTeam}
        {" vs "}
        {match.awayTeam}
      </h1>

      <p>
        {match.date} • {match.time}
      </p>

      <BettingOptions
        match={match}
        onSelectBet={handleSelectBet}
      />

      {selectedBet && (
        <div className="selected-bet">

          <h2>Selected Bet</h2>

          <p>
            {selectedBet.selection}
          </p>

          <p>
            Odds: {selectedBet.odds}
          </p>

          <button>
            Add to Bet Slip
          </button>

        </div>
      )}

    </div>
  );
}

export default MatchDetails;