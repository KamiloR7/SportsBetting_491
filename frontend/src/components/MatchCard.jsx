import { useNavigate } from "react-router-dom";

function MatchCard({ match }) {
  const navigate = useNavigate();

  function openMatch() {
    navigate(`/matches/${match.id}`);
  }

  return (
    <div
      className="match-card"
      onClick={openMatch}
    >

      <p className="league-name">
        {match.league}
      </p>

      <div className="match-teams">

        <h2>{match.homeTeam}</h2>

        <span>VS</span>

        <h2>{match.awayTeam}</h2>

      </div>

      <p>
        {match.date} • {match.time}
      </p>

      <button>
        View Match
      </button>

    </div>
  );
}

export default MatchCard;