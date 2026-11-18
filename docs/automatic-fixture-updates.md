# Automatic local fixture updates

November 15, 2026. The local running application now refreshes provider scores and game status automatically. The ESPN results refresh marked 11 NFL games final, including Raiders 13–Seahawks 21. Only provider-confirmed finals/cancellations trigger the existing idempotent single/parlay settlement. The import was repeated by the worker without duplicate payouts.

## Behavior

- While the backend is running, an opt-in background worker checks ESPN every approximately two minutes. It fetches UTC yesterday, today and tomorrow for NFL, MLB and EPL, retaining US evening games after UTC midnight. This uses nine bounded HTTP requests per cycle rather than re-importing all history.
- The game board and match center reload stored data every 30 seconds. Today's completed games remain under Today with final scores. Browsing in-progress cards retains model odds; the match center can show the latest provider score snapshot.
- The board shows automatic-update frequency and the last successful refresh time. Provider delays mean this is periodic polling, not guaranteed instant/streaming data. A failed refresh leaves the saved data available and displays Updates delayed. Retry backoff is capped at 15 minutes, or the configured base interval if longer. Network requests have a 10-second timeout each.
- The existing refresh importer protects completed results from conflicting corrections, retains internal IDs and never reopens a closed market. Final-result corrections require manual payout review rather than silently paying again. The background loop does not retrain models or change accepted odds.

## Enable on another local installation

After the documented database/model setup, add to ignored backend/.env and restart the backend:

```dotenv
AUTO_REFRESH_ENABLED=true
AUTO_REFRESH_INTERVAL_SECONDS=120
```

Both settings are declared in `.env.example`; automatic refresh defaults off for tests and other deployments. The worker is restricted to a localhost database and clamps polling to 60–3600 seconds. Run one backend worker for this local demo. It stops with the backend; no Windows service or scheduled task is installed. The current local installation is enabled.

GET /health includes a public fixture_refresh status object with enabled/state/interval, last_attempt, last_success, next_refresh and processed-game count. It exposes no account, session or database credentials. This read does not initiate a provider refresh.

## Verification

Focused refresh/normalization/application/access-policy tests: 11 passed. They cover the UTC date window, all three sports, bounded requests, interval limits, local-only writes, failure/backoff behavior and preservation of the last success time. In-progress provider scores remain in_progress and cannot settle bets; incomplete final scores are rejected. Existing settlement and concurrency tests remain in the PR.

On the running app, /health reported enabled=true, interval_seconds=120, state=ready and 13 processed fixtures after a successful cycle. Current NFL status queries returned no in-progress games at that observation, and match 66 was final 13–21. The browser showed current final scores and a successful-refresh timestamp. Screenshot: docs/evidence/automatic-updates-final-results.jpg.

The current headline's second row is the user's exact requested text, Make you call.
