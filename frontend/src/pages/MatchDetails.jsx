import { Link, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import MatchSummary from "../components/MatchSummary";
import { getMatchById } from "../services/matches";

function MatchData({ id }) {
  const [result, setResult] = useState({ loading: true, match: null, error: "" });

  useEffect(() => {
    const controller = new AbortController();
    getMatchById(id, { signal: controller.signal })
      .then((match) => {
        if (!controller.signal.aborted) setResult({ loading: false, match, error: "" });
      })
      .catch((error) => {
        if (!controller.signal.aborted) setResult({ loading: false, match: null, error: error.message });
      });
    return () => controller.abort();
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
