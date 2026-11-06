
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import MatchCard from "../components/MatchCard";
import DemoNotice from "../components/DemoNotice";
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
const MATCH_STATUSES = [
  { value: "scheduled", label: "Upcoming" },
  { value: "in_progress", label: "In progress" },
  { value: "final", label: "Final" },
  { value: "postponed", label: "Postponed" },
  { value: "cancelled", label: "Cancelled" },
];

function getSportOption(value) {
  return SPORT_OPTIONS.find(
    (option) => option.key === value || option.leagueAbbreviation === value
  ) || SPORT_OPTIONS[0];
}

function EmptyUpcomingMatches({ sportOption, status }) {
  return (
    <section className="empty-state" role="status">
      <h2>No {status === "scheduled" ? "upcoming " : ""}{sportOption.leagueAbbreviation} matches</h2>
      <p>Check back when the next schedule is available.</p>
    </section>
  );
}

function LeagueMatches({ sportOption, status }) {
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

        const matches = await getMatches(league.id, { status });

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
  }, [sportOption.leagueAbbreviation, status]);

  if (result.loading) {
    return <p role="status">Loading {sportOption.leagueAbbreviation} matches...</p>;
  }

  if (result.error) {
    return <p role="alert">{result.error}</p>;
  }

  if (!result.matches.length) {
    return (
      <EmptyUpcomingMatches sportOption={sportOption} status={status} />
    );
  }

  return (
    <div className="match-grid">
      {result.matches.map((match) => (
        <MatchCard
          key={match.id}
          match={match}
          league={sportOption.key}
          status={status}
        />
      ))}
    </div>
  );
}

function Dashboard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedSportOption = getSportOption(searchParams.get("league") || DEFAULT_SPORT);
  const requestedStatus = searchParams.get("status");
  const selectedStatus = MATCH_STATUSES.some((item) => item.value === requestedStatus)
    ? requestedStatus
    : "scheduled";

  function updateSelection(key, value) {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set(key, value);
    setSearchParams(nextParams);
  }

  return (
    <div className="dashboard">
      <DemoNotice />
      <header className="dashboard-header">
        <h1>Matches</h1>
        <p>Select a sport and match status to browse available matches.</p>
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
            aria-pressed={selectedSportOption.key === option.key}
            onClick={() => updateSelection("league", option.key)}
          >
            <span className="sport-option-name">{option.sportName}</span>
            <span className="sport-option-league">{option.leagueAbbreviation}</span>
          </button>
        ))}
      </div>

      <div className="match-filter">
        <label htmlFor="match-status">Match status</label>
        <select
          id="match-status"
          value={selectedStatus}
          onChange={(event) => updateSelection("status", event.target.value)}
        >
          {MATCH_STATUSES.map((item) => (
            <option key={item.value} value={item.value}>{item.label}</option>
          ))}
        </select>
      </div>

      <LeagueMatches
        key={`${selectedSportOption.key}-${selectedStatus}`}
        sportOption={selectedSportOption}
        status={selectedStatus}
      />
    </div>
  );
}

export default Dashboard;
