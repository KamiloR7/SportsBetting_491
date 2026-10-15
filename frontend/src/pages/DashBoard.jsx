
import { useEffect, useState } from "react";
import MatchCard from "../components/MatchCard";
import { getLeagues, getMatches } from "../services/matches";

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
    </div>
  );
}

export default Dashboard;
