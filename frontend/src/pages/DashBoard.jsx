
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import MatchCard from "../components/MatchCard";
import DemoNotice from "../components/DemoNotice";
import { getLeagues, getMatches } from "../services/matches";
import { getPredictionHistory } from "../services/predictionHistory";

const SPORT_OPTIONS = [
  {
    key: "football",
    sportName: "Football",
    leagueAbbreviation: "NFL",
    leagueName: "National Football League",
  },
  {
    key: "baseball",
    sportName: "Baseball",
    leagueAbbreviation: "MLB",
    leagueName: "Major League Baseball",
  },
  {
    key: "soccer",
    sportName: "Soccer",
    leagueAbbreviation: "EPL",
    leagueName: "English Premier League",
  },
];

const DEFAULT_SPORT = SPORT_OPTIONS[0].key;

function getSportOption(key) {
  return SPORT_OPTIONS.find((option) => option.key === key) || SPORT_OPTIONS[0];
}

function EmptyUpcomingMatches({ sportOption }) {
  return (
    <section className="empty-state" role="status">
      <h2>No upcoming {sportOption.leagueAbbreviation} matches</h2>
      <p>Check back when the next schedule is available.</p>
    </section>
  );
}

function LeagueMatches({ sportOption }) {
  const [result, setResult] = useState({
    loading: true,
    matches: [],
    error: "",
  });

  useEffect(() => {
    let ignore = false;

    async function load() {
      try {
        const leagues = await getLeagues();
        const league = leagues.find(
          (item) => item.abbreviation === sportOption.leagueAbbreviation
        );

        if (!league) {
          throw new Error(`${sportOption.leagueAbbreviation} is currently unavailable.`);
        }

        const matches = await getMatches(league.id, { status: "scheduled" });

        if (!ignore) {
          setResult({
            loading: false,
            matches,
            error: "",
          });
        }
      } catch (error) {
        if (!ignore) {
          setResult({
            loading: false,
            matches: [],
            error: error.message,
          });
        }
      }
    }

    load();

    return () => {
      ignore = true;
    };
  }, [sportOption.leagueAbbreviation]);

  if (result.loading) {
    return <p role="status">Loading {sportOption.leagueAbbreviation} matches...</p>;
  }

  if (result.error) {
    return <p role="alert">{result.error}</p>;
  }

  if (!result.matches.length) {
    return (
      <EmptyUpcomingMatches sportOption={sportOption} />
    );
  }

  return (
    <div className="match-grid">
      {result.matches.map((match) => (
        <MatchCard key={match.id} match={match} />
      ))}
    </div>
  );
}

function PredictionHistory() {
  const [history] = useState(() => getPredictionHistory());

  

  return (
    <section className="prediction-history" aria-labelledby="prediction-history-heading">
      <div className="prediction-history-heading">
        <h2 id="prediction-history-heading">Recent predictions</h2>
        <p>Saved only in this browser on this device.</p>
      </div>
      {!history.length ? (
        <p role="status">Your generated predictions will appear here.</p>
      ) : (
        <ol className="prediction-history-list">
          {history.map((prediction, index) => {
            const predictedHomeWin = prediction.predicted_outcome === "HOME_WIN";
            const savedDate = new Date(prediction.saved_at);
            const dateLabel = Number.isNaN(savedDate.getTime())
              ? "Date unavailable"
              : savedDate.toLocaleString();
            return (
              <li key={`${prediction.match_id}-${prediction.saved_at}-${index}`}>
                <div>
                  <p className="prediction-history-match">
                    {prediction.home_team_name || "Home team"} vs {prediction.away_team_name || "Away team"}
                    {prediction.sport ? ` · ${prediction.sport}` : ""}
                  </p>
                  <p>Outcome: {predictedHomeWin ? "Home win" : "Not a home win"}</p>
                  <p>
                    Home win {Math.round((prediction.probabilities?.home_win ?? 0) * 100)}%
                    {" · "}
                    Not a home win {Math.round((prediction.probabilities?.not_home_win ?? 0) * 100)}%
                    {" · "}
                    Confidence {Math.round((prediction.confidence ?? 0) * 100)}%
                  </p>
                  <p className="prediction-history-date">{dateLabel}</p>
                </div>
                <Link to={`/matches/${encodeURIComponent(prediction.match_id)}`}>View match</Link>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}

function Dashboard() {
  const [selectedSport, setSelectedSport] = useState(() => {
    try {
      const savedSport = sessionStorage.getItem("selectedSport");
      return SPORT_OPTIONS.some((option) => option.key === savedSport)
        ? savedSport
        : DEFAULT_SPORT;
    } catch {
      return DEFAULT_SPORT;
    }
  });
  const selectedSportOption = getSportOption(selectedSport);

  useEffect(() => {
    try {
      sessionStorage.setItem("selectedSport", selectedSport);
    } catch {
      // Continue if browser storage is unavailable.
    }
  }, [selectedSport]);

  return (
    <div className="dashboard">
      <DemoNotice />
      <header className="dashboard-header">
        <h1>Matches</h1>
        <p>Select a sport to browse upcoming matches.</p>
      </header>

      <div
        className="sport-selector"
        role="group"
        aria-label="Sport selection"
      >
        {SPORT_OPTIONS.map((option) => (
          <button
            key={option.key}
            className="sport-option"
            type="button"
            aria-pressed={selectedSport === option.key}
            onClick={() => setSelectedSport(option.key)}
          >
            <span className="sport-option-name">{option.sportName}</span>
            <span className="sport-option-league">{option.leagueAbbreviation}</span>
          </button>
        ))}
      </div>

      <LeagueMatches
        key={selectedSportOption.key}
        sportOption={selectedSportOption}
      />
      <PredictionHistory />
    </div>
  );
}

export default Dashboard;
