import { useNavigate } from "react-router-dom";

function MatchCard({ match }) {
  const navigate = useNavigate();

  function openMatch() {
    navigate(`/matches/${match.id}`);
  }

  return (
    <div className="match-card" onClick={openMatch}>
      <p className="league-name">{match.league}</p>

      <h2>
        {match.homeTeam} vs {match.awayTeam}
      </h2>

      <div className="probabilities">
        <p>
          {match.homeTeam}: {match.probabilities.homeWin}%
        </p>

        {match.league === "Premier League" && (
          <p>
            Draw: {match.probabilities.draw}%
          </p>
        )}

        <p>
          {match.awayTeam}: {match.probabilities.awayWin}%
        </p>
      </div>

      <p>
        {match.date} • {match.time}
      </p>

      <button>View Match</button>
    </div>
  );
}

export default MatchCard;