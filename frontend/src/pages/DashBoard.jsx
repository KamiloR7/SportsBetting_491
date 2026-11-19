
import { useEffect, useState } from "react";
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

function matchCalendarDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function LeagueMatches({ sportOption }) {
  const [result, setResult] = useState({
    loading: true,
    matches: [],
    error: "",
  });
  const [teamFilter, setTeamFilter] = useState("");
  const [dateFilter, setDateFilter] = useState("");

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

  const teams = [...new Map(result.matches.flatMap((match) => [
    [match.home_team_id, match.home_team_name],
    [match.away_team_id, match.away_team_name],
  ]).filter(([id, name]) => id != null && name).map(([id, name]) => [String(id), name])).entries()]
    .sort((left, right) => left[1].localeCompare(right[1]));
  const visibleMatches = result.matches.filter((match) => {
    const selectedTeam = teamFilter && (
      String(match.home_team_id) === teamFilter || String(match.away_team_id) === teamFilter
    );
    const teamMatches = !teamFilter || selectedTeam;
    const dateMatches = !dateFilter || matchCalendarDate(match.start_time) === dateFilter;
    return teamMatches && dateMatches;
  });

  return (
    <>
      <div className="match-filters" role="group" aria-label={`${sportOption.leagueAbbreviation} match filters`}>
        <label>
          Team
          <select value={teamFilter} onChange={(event) => setTeamFilter(event.target.value)}>
            <option value="">All teams</option>
            {teams.map(([id, name]) => <option key={id} value={id}>{name}</option>)}
          </select>
        </label>
        <label>
          Date
          <input
            type="date"
            value={dateFilter}
            onChange={(event) => setDateFilter(event.target.value)}
            aria-label="Filter matches by date"
          />
        </label>
        {(teamFilter || dateFilter) && (
          <button
            className="clear-match-filters"
            type="button"
            onClick={() => {
              setTeamFilter("");
              setDateFilter("");
            }}
          >
            Clear filters
          </button>
        )}
      </div>
      {visibleMatches.length ? (
        <div className="match-grid" aria-live="polite">
          {visibleMatches.map((match) => <MatchCard key={match.id} match={match} />)}
        </div>
      ) : (
        <p className="filter-empty-state" role="status">
          No {sportOption.leagueAbbreviation} matches match these filters. Clear filters or choose another team or date.
        </p>
      )}
    </>
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
    </div>
  );
}

export default Dashboard;
