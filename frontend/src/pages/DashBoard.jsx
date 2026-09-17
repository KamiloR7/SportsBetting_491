import MatchCard from "../components/MatchCard";
import testMatches from "../data/testMatches";

function Dashboard() {
  return (
    <div>
      <h1>Sports Prediction App</h1>

      <p>Premier League | NBA | NFL</p>

      <h2>Upcoming Matches</h2>

      {testMatches.map((match) => (
        <MatchCard
          key={match.id}
          match={match}
        />
      ))}
    </div>
  );
}

export default Dashboard;