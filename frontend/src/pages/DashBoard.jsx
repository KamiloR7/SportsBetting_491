import FixtureRefreshStatus from "../components/FixtureRefreshStatus";
import ModelInsights from "../components/ModelInsights";
import AccountPanel from "../components/AccountPanel";

import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
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
const MATCH_STATUSES = [
  { value: "matchday", label: "Matchday · today first" },
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
  const league = sportOption.leagueAbbreviation;
  const title = status === "matchday" ? `No ${league} games in progress or coming up.`
    : status === "in_progress" ? `No ${league} games in progress.`
    : status === "scheduled" ? `No upcoming ${league} games.`
    : `No ${league} ${status === "final" ? "completed" : status} games found.`;
  return <section className="empty-state" role="status"><span className="section-kicker">{league} GAME BOARD</span><h2>{title}</h2><p>{["matchday", "scheduled", "in_progress"].includes(status) ? "No fixtures match this view in the available schedule. You can still explore completed games, results and model replays." : "Try another status or a different team search."}</p><Link to={`/dashboard?league=${sportOption.key}&status=final`}>Explore completed {league} games →</Link></section>;
}

const PAGE_SIZE = 12;

function LeagueMatches({ sportOption, status, search, offset, onPage, returnParams }) {
  const [result, setResult] = useState({
    loading: true,
    matches: [],
    error: "",
  });

  useEffect(() => {
    let ignore = false;
    let running = false;

    async function load() {
      if (running) return;
      running = true;
      try {
        const leagues = await getLeagues();
        const league = leagues.find(
          (item) => item.abbreviation === sportOption.leagueAbbreviation
        );

        if (!league) {
          throw new Error(`${sportOption.leagueAbbreviation} is currently unavailable.`);
        }

        const matches = await getMatches(league.id, { status, search, offset, limit: status === "today_results" ? 200 : PAGE_SIZE });

        if (status === "matchday") {
          const today = new Date(); today.setHours(0, 0, 0, 0);
          const yesterday = new Date(today); yesterday.setDate(today.getDate() - 1);
          if (matches.some(match => Date.parse(match.start_time) < (match.status === "in_progress" ? yesterday : today).getTime())) {
            throw new Error("The server returned older games for Matchday. Restart the updated backend and refresh this page.");
          }
        }
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
      } finally { running = false; }
    }

    load();
    const timer = setInterval(load, 30000);

    return () => {
      ignore = true;
      clearInterval(timer);
    };
  }, [sportOption.leagueAbbreviation, status, search, offset]);

  if (status === "today_results") {
    if (result.loading) return <p className="results-loading" role="status">Loading today’s completed games…</p>;
    if (result.error) return <p role="alert">Today’s results are temporarily unavailable.</p>;
    if (!result.matches.length) return null;
    return <details className="played-today"><summary><span><span className="section-kicker">THE FINAL WHISTLE</span><strong>Played today</strong></span><span>{result.matches.length} completed {result.matches.length === 1 ? "game" : "games"}<span className="results-chevron" aria-hidden="true">⌄</span></span></summary><p>Final scores and model replays. These games are closed for betting.</p><div className="match-grid">{result.matches.map(match => <MatchCard key={match.id} match={match} returnParams={returnParams}/>)}</div></details>;
  }

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

  const groups = new Map();
  result.matches.forEach(match => {
    const date = new Date(match.start_time);
    const isToday = date.toDateString() === new Date().toDateString();
    const dateLabel = date.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric", year: "numeric" });
    const day = status === "matchday" && match.status === "in_progress" ? "In progress" : `${isToday ? "Today · " : ""}${dateLabel}`;
    if (!groups.has(day)) groups.set(day, []);
    groups.get(day).push(match);
  });
  return <>
    <div className="results-toolbar"><span>{result.matches.length} games · {sportOption.leagueAbbreviation}</span><span>Your local time · {status === "matchday" ? "In progress first · upcoming games" : status === "in_progress" ? "No live score feed" : "Grouped by game day"}</span></div>
    <div className="fixture-days">{[...groups].map(([day, matches]) => <section className={`fixture-day ${day === "In progress" ? "day-in-progress" : day.startsWith("Today") ? "day-today" : ""}`} key={day} aria-label={day}><div className="fixture-day-heading"><h3>{day}</h3><span>{matches.length} {matches.length === 1 ? "game" : "games"}</span></div><div className="match-grid">{matches.map(match => <MatchCard key={match.id} match={match} returnParams={returnParams} />)}</div></section>)}</div>
    <div className="pagination"><button disabled={offset === 0} onClick={() => onPage(Math.max(0, offset - PAGE_SIZE))}>← Previous</button><span>Page {Math.floor(offset / PAGE_SIZE) + 1}</span><button disabled={result.matches.length < PAGE_SIZE} onClick={() => onPage(offset + PAGE_SIZE)}>Next →</button></div>
  </>;

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
                  <p>{prediction.mode === "historical_replay" ? "Historical replay" : "Pregame forecast"} · Outcome: {predictedHomeWin ? "Home win" : "Not a home win"}{prediction.mode === "historical_replay" ? (prediction.correct ? " · Matched result" : " · Missed result") : ""}</p>
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
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedSportOption = getSportOption(searchParams.get("league") || DEFAULT_SPORT);
  const requestedStatus = searchParams.get("status");
  const selectedStatus = MATCH_STATUSES.some((item) => item.value === requestedStatus)
    ? requestedStatus
    : "matchday";

  function updateSelection(key, value) {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set(key, value);
    if (key === "league") nextParams.set("status", "matchday");
    if(key !== "offset") nextParams.delete("offset");
    setSearchParams(nextParams);
  }

  return (
    <div className={`dashboard board-${selectedSportOption.key}`}>
      <DemoNotice />
      <AccountPanel />
      <header className="dashboard-header">
        <div className="eyebrow"><span/> THE MATCHDAY DESK</div><h1>Every game.<br/><em>Make you call</em></h1>
        <p>Explore the fixtures. Read the model. Make your pick.</p><div className="hero-label">NFL <span>•</span> MLB <span>•</span> PREMIER LEAGUE</div>
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
            <span className="sport-option-name"><span className="sport-symbol" aria-hidden="true">{option.key === "football" ? "◈" : option.key === "baseball" ? "◉" : "⬡"}</span>{option.sportName}</span>
            <span className="sport-option-league">{option.leagueAbbreviation}</span>
          </button>
        ))}
      </div>

      <div className="fixtures-heading"><div><span className="section-kicker">THE BOARD</span><h2>{selectedSportOption.leagueAbbreviation} matchups</h2><Link className="standings-inline-link" to={`/standings?league=${selectedSportOption.leagueAbbreviation}`}>View {selectedSportOption.leagueAbbreviation} standings ↗</Link></div><label className="search-field"><span className="sr-only">Search teams</span><input type="search" placeholder="Search a team…" value={searchParams.get("search") || ""} onChange={e=>updateSelection("search",e.target.value)}/></label></div><div className="match-filter">
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

      <FixtureRefreshStatus/>
      <LeagueMatches
        key={`${selectedSportOption.key}-${selectedStatus}-${searchParams.get("search") || ""}-${searchParams.get("offset") || "0"}`}
        returnParams={new URLSearchParams({ ...Object.fromEntries(searchParams), league: selectedSportOption.key, status: selectedStatus })}
        sportOption={selectedSportOption}
        status={selectedStatus}
        search={searchParams.get("search") || ""}
        offset={Math.max(0,Number(searchParams.get("offset"))||0)}
        onPage={offset=>updateSelection("offset",String(offset))}
      />
      {selectedStatus === "matchday" && <LeagueMatches key={`results-${selectedSportOption.key}-${searchParams.get("search") || ""}`} sportOption={selectedSportOption} status="today_results" search={searchParams.get("search") || ""} offset={0} returnParams={new URLSearchParams({ ...Object.fromEntries(searchParams), league: selectedSportOption.key, status: "matchday" })}/>}
      <div className="insights-link-row"><Link to="/insights">How are predictions and percentages calculated? Explore Model Insights →</Link></div>
      <ModelInsights />
      <PredictionHistory />
    </div>
  );
}

export default Dashboard;
