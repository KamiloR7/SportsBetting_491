import { Link } from "react-router-dom";
import MatchSummary from "./MatchSummary";

function MatchCard({ match, league, status }) {
  const params = new URLSearchParams({ league, status });

  return (
    <article className="match-card">
      <MatchSummary match={match} />
      <Link to={`/matches/${match.id}?${params.toString()}`}>View Match</Link>
    </article>
  );
}

export default MatchCard;
