function MatchCard({ match }) {
  return (
    <div>
      <p>{match.league}</p>

      <h2>
        {match.homeTeam} vs {match.awayTeam}
      </h2>

      <p>
        {match.date} at {match.time}
      </p>

      <button>View Match</button>
    </div>
  );
}

export default MatchCard;