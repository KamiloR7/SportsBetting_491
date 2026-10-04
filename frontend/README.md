# Sprint 2 frontend

React + Vite + JavaScript + React Router. The current frontend browses NBA,
NFL, and EPL matches through the backend API; the active match screens do not
use mock match data.

## Setup

Use Node.js and npm compatible with the installed Vite version. From the
repository root:

```sh
cd frontend
npm ci
npm run dev
```

Open the URL Vite prints (usually `http://localhost:5173/`), or go directly to
`/dashboard`. Stop Vite with Control + C.

The expected backend is `http://127.0.0.1:8000`. By default, `services/api.js`
uses `/api`; the Vite development proxy strips that prefix and forwards requests
to the backend. For example, `/api/leagues` becomes backend `/leagues`.

`VITE_API_URL` overrides the request base URL; a trailing slash is removed.
Set it before starting Vite, for example:

```sh
VITE_API_URL=http://127.0.0.1:8000 npm run dev
```

A direct cross-origin URL requires backend CORS support. Restart Vite after
changing environment settings. Production builds use the value supplied at
build time. Without an override, production hosting must proxy `/api`.
`npm run preview` does not use the development API proxy; production hosts also
need SPA fallback for direct route loads.

## Screens, components, and navigation

Routes live in `src/App.jsx`, using `BrowserRouter`:

| Route | Component | Current behavior |
| --- | --- | --- |
| `/` | `SplashScreen` | Branding screen; redirects to `/login` after 2.5 seconds. |
| `/login` | `Login` | Prototype form; submission navigates to `/dashboard`. It does not authenticate with the backend and currently logs entered values to the console. |
| `/dashboard` | `Dashboard` in `pages/DashBoard.jsx` | NBA/NFL/EPL selection, API loading, empty/error states, and match cards. |
| `/matches/:id` | `MatchDetails` | Fetches one match, renders its summary and neutral-site context, and links back to `/dashboard`. |

The flow is splash → login → dashboard → match card → details → Back to matches.
There is no direct splash-to-dashboard link or register/account route.
Dashboard selection is component state initialized to NBA; it resets on remount,
including returning from details. Selection is not stored in the URL or browser
history. League buttons expose selection through `aria-pressed`.

- `components/MatchCard.jsx`: reusable match article with a `View Match` link
  to `/matches/${match.id}`.
- `components/MatchSummary.jsx`: shared league, teams, local date/time, status,
  and available scores for cards and details.
- `pages/MatchDetails.jsx`: validates IDs through the service, handles loading,
  missing/error results, and displays neutral-site context without inferring venue.
- `services/api.js`: shared fetch wrapper and readable connection, HTTP, and
  JSON errors; preserves abort errors.
- `services/matches.js`: league/list/detail requests and positive integer ID
  validation. Pages pass abort signals and cancel requests on cleanup.
- `App.css` and `index.css`: screen styles and shared typography/layout;
  dashboard and details have scoped long-text wrapping.

Legacy `services/odds.js`, `services/bets.js`, `data/testMatches.js`, and
`components/BettingOptions.jsx` are not used by the current routed match screens.
They are not the Sprint 2 match API contract.

## Consumed API contract

| Request | Current use |
| --- | --- |
| `GET /leagues` | Resolve the selected NBA/NFL/EPL abbreviation to its backend ID. |
| `GET /matches?league_id=<id>` | Load matches for that resolved ID. |
| `GET /matches/{match_id}` | Load one match for the details route. |

League selection consumes only each league's `id` and `abbreviation`.
Match fields consumed by the UI are:

| Field | Use |
| --- | --- |
| `id` | Card key and details link. |
| `league_name` | League/competition text; missing value shows `League unavailable`. |
| `home_team_name`, `away_team_name` | Team headings with unavailable fallbacks. |
| `start_time` | Browser-local medium date and short time; null, undefined, blank, whitespace-only, or invalid values show `Date/time unavailable`. |
| `status` | Text with underscores replaced by spaces; missing value shows `Unavailable`. |
| `home_score`, `away_score` | Home–away scores when either is present; zero is preserved, a missing side shows `—`. |
| `neutral_site` | Details only: true → Yes, false → No, null/undefined → Unavailable. |

Do not assume league IDs are fixed or add NBA-specific periods, statistics, or
score labels to the shared components.

## Backend/Data dependencies and current limitations

The local matches table has no rows in the reviewed environment. NBA, NFL, and
EPL list requests returned empty arrays, and match ID `1` returned 404. Successful
populated list → details testing is therefore a Backend/Data dependency, not a
frontend bug. Do not fabricate records to mark that check complete.

The current match response does not include predictions, odds, venue/location,
sport metadata, or historical statistics. Neutral-site status does not identify
a venue. League names come from the response; no unavailable context is inferred.
A separate backend history endpoint exists but is not consumed by these screens.

The prototype login and dashboard selection reset described above remain current
usability limitations. Populated layouts and actual browser viewport behavior
still need verification.

## Testing status and remaining checks

Evidence from the Sprint 2 frontend review:

- Live API checks: NBA/NFL/EPL league IDs resolved; all three lists returned
  `200` with `[]`; `/matches/1` returned 404.
- Isolated component rendering: all three empty states show
  `No [league] matches are available.` without cards/placeholders or crashes.
- Runtime-only API failure simulation: connection failure, HTTP 404/500, and
  invalid JSON produce readable dashboard/details alerts; abort errors are
  preserved. Backend configuration was not changed and no match records were added.
- Invalid ID service checks: `abc` and `0` are rejected before an API request.
- Source review: loading/empty states retain `role="status"`, error states retain
  `role="alert"`, request cleanup preserves abort handling, and back links remain
  visible on details errors. Details loading and error markup were also rendered
  in isolation.
- Navigation source review confirmed splash/login/dashboard/card/details paths.
  Vite returned the app entry HTML with `200` for direct `/dashboard` and
  `/matches/1` requests; this does not prove browser rendering or refresh behavior.
- Static responsive review confirmed fluid root sizing, smaller headings at narrow
  widths, and `overflow-wrap: anywhere` on dashboard/details for long names.
  Actual browser layout and Back/Forward interactions remain untested.
- Build, lint, and whitespace checks passed after the frontend changes.
  The isolated checks were temporary review scripts, not a committed test suite.

Run from `frontend/`:

```sh
npm run build
npm run lint
git diff --check
```

Remaining browser checks: navigate through the prototype routes, use Back/Forward,
refresh `/dashboard` and `/matches/1`, switch leagues quickly, and inspect dashboard
empty states and details loading/error states at narrow widths. Once real backend
matches exist, verify card → populated details → back, local dates, zero scores,
long team/competition names, and neutral-site values across NBA/NFL/EPL.

## Handoff

Keep requests in `services/matches.js` and shared transport/error handling in
`services/api.js`; routes belong in `App.jsx`. Reuse `MatchSummary` and `MatchCard`
across sports. Extend details context only when the API actually supplies fields.
When prediction data becomes available later, confirm its contract first, add the
request in the service layer, and add a dedicated details component with its own
loading/unavailable/error behavior. Do not treat legacy mock odds as real API data
or assume NBA-specific fields apply to NFL/EPL.
