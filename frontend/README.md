# Sprint 2 frontend

The dashboard resolves NBA, NFL, and EPL IDs from `GET /leagues`, then loads
`GET /matches?league_id=<id>`. Match details use `GET /matches/{match_id}`.
Dates and times display in the browser's local timezone. Predictions and odds
are unavailable in this backend contract.

## Run

From the repository root:

```sh
cd frontend
npm ci
npm run dev
```

With the backend running at `http://127.0.0.1:8000`, open
`http://localhost:5173/dashboard` (or the URL Vite prints).
The Vite development proxy forwards `/api` requests to the backend without
requiring backend CORS changes.

To use a different API URL, set `VITE_API_URL` when starting Vite. Direct
cross-origin API URLs require the server to allow the frontend origin.
Production hosting must proxy `/api` to the backend or supply a suitable
`VITE_API_URL` at build time; the development proxy does not apply to preview.

## Checks

```sh
npm run lint
npm run build
```

Manual integration checks with a configured and populated backend:

- Select NBA, NFL, and EPL. Confirm each request uses the ID returned by
  `/leagues`, and cards show teams, league, local date/time, status, and available
  scores (including zero).
- Open a card and refresh its details URL. Confirm the match is fetched by ID.
- Switch leagues quickly; only the selected league's data should appear.
- A league with no matches should show an empty message.
- Stop the backend and reload; a readable error should replace the loading state.
- Open `/matches/999999999` for a nonexistent match and `/matches/invalid` for an
  invalid ID; confirm readable errors.
- Cards and details should work without predictions or odds.
