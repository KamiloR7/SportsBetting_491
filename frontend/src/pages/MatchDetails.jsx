import { useParams } from "react-router-dom";
import mockMatches from "../data/testMatches";

function MatchDetails() {
  const { id } = useParams();

  const match = mockMatches.find(
    (match) =>
      match.id === Number(id)
  );

  if (!match) {
    return <h2>Match not found</h2>;
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

      <div className="team-context">

        <div>
          <h3>{match.homeTeam}</h3>
          <p>Recent Form: W W L W W</p>
        </div>

        <div>
          <h3>{match.awayTeam}</h3>
          <p>Recent Form: W L W L W</p>
        </div>

      </div>

      <button>
        Run AI Prediction
      </button>

    </div>
  );
}

export default MatchDetails;