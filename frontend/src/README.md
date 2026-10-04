# Frontend source guide

The current setup, routes, API fields, testing status, and Sprint 2 handoff are
maintained in [the main frontend README](../README.md).

- `pages/`: routed screens (`SplashScreen`, `Login`, `DashBoard`, `MatchDetails`).
- `components/`: reusable `MatchCard` and `MatchSummary` for the active match UI.
- `services/api.js`: shared request/error handling.
- `services/matches.js`: league, match-list, and match-detail API calls.
- `App.jsx`: React Router routes; `main.jsx`: React entry point.
- `App.css`, `index.css`: screen and shared styles.

This replaces the outdated Sprint 1 mock-data guide. The current match screens
load backend data; there is no register route or implemented betting flow in the
current navigation. Legacy mock/odds/bets files are not used by those screens.