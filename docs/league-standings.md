# League standings

The Standings page is available from the main navigation and each sport's match board. It is public, read-only league information and does not change wallets, bets, predictions or the model's six features.

## Views

- NFL: AFC and NFC tables (16 teams each) plus an overall record comparison covering all 32 teams. Conferences preserve the provider's order. Overall sorts by winning percentage and keeps source order for ties; it is explicitly not a playoff-seeding projection. Columns include W/L/T, winning percentage, points for/against, differential and streak.
- EPL: all 20 clubs, provider rank and points, played/W/D/L, goals for/against and goal difference. Provider points and deductions are retained instead of recomputing 3W+D. Points appear first for readability on narrower screens.
- MLB: six five-team divisions, AL/NL tables with 15 teams each, and all 30 teams overall. The official division/league/sport ranks are used. Games behind is read from the corresponding grouping, not reused incorrectly across views. Columns include W/L, percentage, GB, runs scored/allowed, differential and streak.

Tables use actual logos, team search and links to each team's match board. Filtering preserves the team's original position rather than renumbering the search results. Tables scroll horizontally on smaller screens. League/view selections are bookmarkable via /standings?league=NFL&view=overall (also EPL and MLB).

## Data and freshness

NFL/EPL use ESPN standings; MLB uses the official MLB Stats API's regular-season standings, not the app's incomplete historical match sample. The verified initial tables contain NFL 2026, EPL 2026-27 and MLB 2026. The MLB fetch chooses the latest year with played regular-season games and can fall back one season if the current year has no played games. It does not label older standings using a future season from a provider's top-level metadata.

GET /standings/{league} supports NFL, EPL and MLB. A five-minute per-league cache coalesces requests and saves the latest normalized snapshot under ignored build/standings. Open pages check the cache every minute. On a failed update the last good table is retained and marked stale; a cold failure returns a clear 503 instead of invented records. Failed fetches are throttled for 60 seconds. Network calls have 12-second timeouts. These updates are independent of the two-minute live-fixture refresh and may lag live scores.

The API validates expected team counts, duplicate identities, consistent season labels, records, percentages and MLB ranks. Unknown/incomplete data is not silently turned into zero records. Team logo/color matching uses the existing verified catalog, including the MLB Stats API's D-backs nickname for Arizona.

No database migration, model retraining, paid subscription or API key is required. Source table data is fetched at runtime, not committed as a frozen standings dataset. Normalized cache snapshots remain local.

## Validation

Focused standings/cache/access/branding checks: 14 passed. Coverage includes AFC/NFC and overall ordering, EPL point deductions, six MLB divisions plus AL/NL/overall, proper games-behind fields, season selection, incomplete/duplicate/mixed-season rejection, cache TTL/persistence/stale fallback/retry throttling, unsupported leagues and public access. Frontend build and lint passed.

Browser verification: NFL conference and overall views, the EPL table, and MLB division/league/overall views. Provider team counts were 32/20/30 and all rows had logo metadata. Screenshots: docs/evidence/nfl-conference-standings.jpg, nfl-overall-standings.jpg, epl-league-table.jpg, mlb-division-standings.jpg, mlb-league-standings.jpg and mlb-overall-standings.jpg.
