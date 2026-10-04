import { Link } from "react-router-dom";
import MatchSummary from "./MatchSummary";

function MatchCard({ match }) {
  return (
    <article className="match-card">
      <MatchSummary match={match} />
      <Link to={`/matches/${match.id}`}>View Match</Link>
    </article>
  );
}

export default MatchCard;
