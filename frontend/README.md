# Sprint 3 match UI

React, Vite, and React Router provide the NFL, MLB, and EPL match-prediction
workflow. The routed match screens use the backend API; legacy mock betting data
is not used.

## Run locally

Start the backend on `http://127.0.0.1:8000`, then from `frontend/`:

```sh
npm ci
npm run dev
```

Open `/dashboard` on the URL printed by Vite. The default `/api` base path is
proxied to the backend in development. `VITE_API_URL` can override the base URL;
direct cross-origin requests require backend CORS support. Production hosting
must proxy `/api` and provide SPA fallback for direct route loads.

For a full walkthrough without PostgreSQL, start the synthetic demo backend
from `backend/` with `python -m uvicorn app.database.demo:app --port 8000`.
Its matches and trained model are local examples, not live sports data.

## User flow

1. Select Football/NFL, Baseball/MLB, or Soccer/EPL on `/dashboard`.
2. Choose a scheduled match to open `/matches/:id`.
3. Review the match summary and each team's three most recent completed matches.
4. Select **Run Prediction** to generate an outcome and probabilities.

The selected sport is retained in `sessionStorage` for the browser session.
Loading, empty, and error states are shown for the list, details, history, and
prediction request. An unavailable backend is an error; an empty list means the
backend returned no scheduled matches.

The `/login` page remains a prototype navigation screen and does not authenticate
with the backend. It currently logs entered values to the console; do not enter
real credentials there.

## API contract

| Request | Use |
| --- | --- |
| `GET /leagues` | Resolve NFL, MLB, or EPL to its current league ID. |
| `GET /matches?league_id=<id>&status=scheduled` | List upcoming matches. |
| `GET /matches/{id}` | Load one match. |
| `GET /matches/history?league_id=<id>&team_id=<id>&limit=3` | Load recent completed results for each team. |
| `POST /predictions/matches/{id}` | Run the trained local baseline on pre-match history. |

Prediction responses contain `predicted_outcome`, `home_win_probability`,
`away_win_probability`, optional `draw_probability` for EPL, `confidence`, and
the predicted winner's name when the outcome is not a draw. A missing model,
unavailable database, or insufficient team history produces an explicit error.

## Verification and limits

From `frontend/`, run `npm run lint` and `npm run build`. Backend tests include an
isolated NFL/MLB/EPL API flow with matches, history, and generated predictions.
For the live browser path, configure PostgreSQL, load the schema, seed matches,
and train local artifacts as described in `backend/README.md`.

The local development match seed is synthetic demo data, not a live schedule.
The EPL draw probability is an early baseline estimate that splits the model's
not-home-win probability using historical draw frequency. It is not a separately
trained three-class model. Match responses do not include venue or odds data.
