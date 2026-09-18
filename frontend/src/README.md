VIGOR Frontend

Beginner-friendly setup and handoff guide for the VIGOR sports betting
frontend.

Stack: React + Vite + JavaScript + React Router
Sports: NBA, NFL, Premier League
Current stage: Sprint 1 frontend skeleton using mock match/odds data

1. Quick Start

First-time setup

Make sure these commands work:

node --version
npm --version
git --version

On macOS with Homebrew, install Node.js with:

brew install node

Clone the project and start the frontend:

git clone YOUR_REPOSITORY_URL
cd YOUR_REPOSITORY_NAME/frontend
npm install
npm run dev

Open the local address Vite displays, usually:

http://localhost:5173/

Stop the server with Control + C.

2. Current User Flow

VIGOR Splash
    ↓
Login / Register
    ↓
Dashboard
    ↓
NBA | NFL | Premier League
    ↓
Match Card
    ↓
Match Details
    ↓
Betting Options / Odds
    ↓
Select Bet

Sprint 1 uses mock data. Future sprints should replace the data source
without rebuilding the UI.

3. Frontend Structure

frontend/
├── src/
│   ├── assets/          # Images/logos
│   ├── components/      # Reusable UI
│   │   ├── MatchCard.jsx
│   │   ├── BettingOptions.jsx
│   ├── data/
│   │   └── testMatches.js   # Temporary mock data
│   ├── pages/           # Full screens
│   │   ├── SplashScreen.jsx
│   │   ├── Login.jsx
│   │   ├── Dashboard.jsx
│   │   └── MatchDetails.jsx
│   ├── services/        # Future backend communication
│   │   ├── api.js
│   │   ├── matches.js
│   │   ├── odds.js
│   │   └── bets.js
│   ├── App.jsx          # Routes
│   ├── App.css
│   ├── index.css
│   └── main.jsx
├── package.json
└── vite.config.js

Simple rule

pages/ = complete screens

components/ = reusable pieces of screens

data/ = temporary mock data

services/ = backend/API functions

App.jsx = navigation/routes

4. Important Components

MatchCard

One reusable card for NBA, NFL, and Premier League matches.

<MatchCard match={match} />

It should display the league, teams, date/time, and allow the user to
open Match Details.

BettingOptions

Displays betting choices for the selected match.

NBA/NFL may show:

Moneyline
Spread
Total

Premier League may show:

Home Win
Draw
Away Win

Keep the component reusable. Pass data through props instead of
hardcoding teams.

5. Mock Data

During Sprint 1, match data can live in:

src/data/testMatches.js

Example:

const testMatches = [
  {
    id: 1,
    league: "NBA",
    homeTeam: "Lakers",
    awayTeam: "Warriors",
    date: "Oct 20",
    time: "7:30 PM",
    odds: {
      homeMoneyline: "+120",
      awayMoneyline: "-105",
      homeSpread: "+3.5",
      awaySpread: "-3.5",
      total: 225.5,
    },
  },
];

export default testMatches;

These are development values only. Every match must have a unique id.

6. Navigation With React Router

Install React Router if needed:

npm install react-router-dom

App.jsx controls the routes:

<Routes>
  <Route path="/" element={<SplashScreen />} />
  <Route path="/login" element={<Login />} />
  <Route path="/register" element={<Register />} />
  <Route path="/dashboard" element={<Dashboard />} />
  <Route path="/matches/:id" element={<MatchDetails />} />
</Routes>

/matches/:id is dynamic. For /matches/2, useParams() returns the
ID "2".

const { id } = useParams();

const match = testMatches.find(
  (match) => match.id === Number(id)
);

7. API Skeleton

Sprint 1 only needs the service skeleton. The backend endpoints can
be connected later.

React Component
      ↓
services/
      ↓
Backend API (future)

services/api.js

Shared request configuration:

const BASE_URL =
  import.meta.env.VITE_API_URL ||
  "http://localhost:8000";

export async function apiRequest(endpoint, options = {}) {
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json();
}

Planned service functions

matches.js

export function getMatches() {
  return apiRequest("/matches");
}

export function getMatchById(id) {
  return apiRequest(`/matches/${id}`);
}

odds.js

export function getOddsByMatchId(id) {
  return apiRequest(`/matches/${id}/odds`);
}

bets.js

export function addBet(bet) {
  return apiRequest("/bets", {
    method: "POST",
    body: JSON.stringify(bet),
  });
}

Do not put backend URLs directly inside pages/components.

8. Moving From Mock Data to Real APIs

Sprint 1

testMatches.js → React UI

Future sprint

Backend → services/matches.js → React UI
Backend → services/odds.js   → React UI

The goal is to change where the data comes from, not redesign the
frontend.

For example, replace:

import testMatches from "../data/testMatches";

with:

import { getMatches } from "../services/matches";

when the backend is ready.

9. Adding Future Features

New page

Create src/pages/BetHistory.jsx.

Add the component.

Add a route in App.jsx.

<Route path="/history" element={<BetHistory />} />

New reusable component

Create it in src/components/.

Examples:

BetSlip.jsx
OddsButton.jsx
LeagueFilter.jsx

Avoid copying the same component separately for NBA, NFL, and Premier
League unless the interfaces truly require different implementations.

10. Useful Commands

npm install       # Install dependencies
npm run dev       # Start development server
npm run lint      # Check JavaScript/React issues
npm run build     # Create production build
npm run preview   # Preview production build