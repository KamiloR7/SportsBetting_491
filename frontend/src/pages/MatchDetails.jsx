import { Link, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import MatchSummary from "../components/MatchSummary";
import { getMatchById, getMatchHistory, runMatchPrediction } from "../services/matches";

function teamPlayedMatch(match, teamId) {
  if (teamId == null) return false;
  return match.home_team_id === teamId || match.away_team_id === teamId;
}

function resultForTeam(match, teamId) {
  if (teamId == null) return "Result unavailable";

  if (match.home_score == null || match.away_score == null) {
    return "Result unavailable";
  }

  const isHomeTeam = match.home_team_id === teamId;
  const teamScore = isHomeTeam ? match.home_score : match.away_score;
  const opponentScore = isHomeTeam ? match.away_score : match.home_score;

  if (teamScore === opponentScore) return "Draw";
  return teamScore > opponentScore ? "Win" : "Loss";
}

function scoreForTeam(match, teamId) {
  const isHomeTeam = match.home_team_id === teamId;
  const teamScore = isHomeTeam ? match.home_score : match.away_score;
  const opponentScore = isHomeTeam ? match.away_score : match.home_score;
  return `${teamScore ?? "-"}-${opponentScore ?? "-"}`;
}

function TeamHistory({ headingId, label, teamId, history }) {
  const recentMatches = history
    .filter((match) => teamPlayedMatch(match, teamId))
    .slice(0, 3);

  return (
    <section className="team-history" aria-labelledby={headingId}>
      <h3 id={headingId}>{label}</h3>
      {!recentMatches.length ? (
        <p>Recent completed matches are unavailable.</p>
      ) : (
        <ul>
          {recentMatches.map((match) => {
            const opponentName = match.home_team_id === teamId
              ? match.away_team_name
              : match.home_team_name;

            return (
              <li key={`${label}-${match.id}`}>
                <span>{resultForTeam(match, teamId)}</span>
                <span>vs {opponentName || "Opponent unavailable"}</span>
                <span aria-label="Team score to opponent score">{scoreForTeam(match, teamId)}</span>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function HistoricalTeamContext({ match }) {
  const [result, setResult] = useState({
    loading: Boolean(match.league_id && match.home_team_id && match.away_team_id),
    homeHistory: [],
    awayHistory: [],
    error: "",
  });

  useEffect(() => {
    let ignore = false;

    if (!match.league_id || !match.home_team_id || !match.away_team_id) {
      return undefined;
    }

    Promise.all([
      getMatchHistory(match.league_id, match.home_team_id),
      getMatchHistory(match.league_id, match.away_team_id),
    ])
      .then(([homeHistory, awayHistory]) => {
        if (!ignore) {
          setResult({
            loading: false,
            homeHistory: homeHistory.filter((item) => item.id !== match.id),
            awayHistory: awayHistory.filter((item) => item.id !== match.id),
            error: "",
          });
        }
      })
      .catch(() => {
        if (!ignore) {
          setResult({
            loading: false,
            homeHistory: [],
            awayHistory: [],
            error: "History unavailable",
          });
        }
      });

    return () => {
      ignore = true;
    };
  }, [match.id, match.league_id, match.home_team_id, match.away_team_id]);

  if (result.loading) {
    return <p role="status">Loading team history...</p>;
  }

  if (result.error) {
    return <p role="alert">Historical team context is unavailable.</p>;
  }

  return (
    <div className="team-history-grid">
      <TeamHistory
        headingId="home-team-history-heading"
        label={match.home_team_name || "Home team"}
        teamId={match.home_team_id}
        history={result.homeHistory}
      />
      <TeamHistory
        headingId="away-team-history-heading"
        label={match.away_team_name || "Away team"}
        teamId={match.away_team_id}
        history={result.awayHistory}
      />
    </div>
  );
}

function formatPercent(value) {
  return value == null
    ? "Unavailable"
    : `${Math.round(Number(value) * 100)}%`;
}

function predictionOutcome(prediction) {
  if (prediction.predicted_outcome === "draw") return "Draw";
  return prediction.predicted_winner_name || "Outcome unavailable";
}

function PredictionPanel({ match }) {
  const [result, setResult] = useState({
    loading: false,
    prediction: null,
    error: "",
  });

  async function handleRunPrediction() {
    setResult({
      loading: true,
      prediction: null,
      error: "",
    });

    try {
      const prediction = await runMatchPrediction(match.id);
      setResult({
        loading: false,
        prediction,
        error: "",
      });
    } catch (error) {
      setResult({
        loading: false,
        prediction: null,
        error: error.message,
      });
    }
  }

  return (
    <section className="match-details-context prediction-panel" aria-labelledby="prediction-heading">
      <div className="prediction-panel-header">
        <h2 id="prediction-heading">Prediction</h2>
        <button
          type="button"
          onClick={handleRunPrediction}
          disabled={result.loading}
        >
          {result.loading ? "Running..." : "Run Prediction"}
        </button>
      </div>

      {result.error && (
        <p role="alert">{result.error}</p>
      )}

      {result.prediction && (
        <dl className="prediction-results">
          <div>
            <dt>Predicted outcome</dt>
            <dd>{predictionOutcome(result.prediction)}</dd>
          </div>
          <div>
            <dt>Home win probability</dt>
            <dd>{formatPercent(result.prediction.home_win_probability)}</dd>
          </div>
          <div>
            <dt>Away win probability</dt>
            <dd>{formatPercent(result.prediction.away_win_probability)}</dd>
          </div>
          {result.prediction.draw_probability != null && (
            <div>
              <dt>Estimated draw probability</dt>
              <dd>{formatPercent(result.prediction.draw_probability)}</dd>
            </div>
          )}
          <div>
            <dt>Confidence</dt>
            <dd>{formatPercent(result.prediction.confidence)}</dd>
          </div>
        </dl>
      )}

      {!result.error && !result.prediction && !result.loading && (
        <p>Run the model to view the predicted outcome and confidence.</p>
      )}
    </section>
  );
}

function MatchData({ id }) {
  const [result, setResult] = useState({ loading: true, match: null, error: "" });

  useEffect(() => {
    let ignore = false;

    getMatchById(id)
      .then((match) => {
        if (!ignore) setResult({ loading: false, match, error: "" });
      })
      .catch((error) => {
        if (!ignore) setResult({ loading: false, match: null, error: error.message });
      });
    return () => {
      ignore = true;
    };
  }, [id]);

  if (result.loading) return <p role="status">Loading match…</p>;
  if (result.error) return <p role="alert">{result.error}</p>;
  if (!result.match) return <p role="status">This match is unavailable.</p>;

  return (
    <>
      <div className="match-details-summary">
        <MatchSummary match={result.match} />
      </div>
      <section className="match-details-context" aria-labelledby="match-context-heading">
        <h2 id="match-context-heading">Match context</h2>
        <p>Neutral site: {result.match.neutral_site === true
          ? "Yes"
          : result.match.neutral_site === false ? "No" : "Unavailable"}</p>
      </section>
      <section className="match-details-context" aria-labelledby="team-context-heading">
        <h2 id="team-context-heading">Historical team context</h2>
        <HistoricalTeamContext key={result.match.id} match={result.match} />
      </section>
      <PredictionPanel match={result.match} />
    </>
  );
}

function MatchDetails() {
  const { id } = useParams();
  return (
    <div className="match-details">
      <Link to="/dashboard">Back to matches</Link>
      <h1>Match details</h1>
      <MatchData key={id} id={id} />
    </div>
  );
}

export default MatchDetails;
