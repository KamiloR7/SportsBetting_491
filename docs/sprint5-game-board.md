# Game board and return navigation

November 15, 2026. The Explore board now requests 12 games per page instead of 30, groups them by local calendar day and uses compact cards with distinct sport accents. Page navigation remains server-paginated. Search, sport, status and offset are included in each match link and preserved by the styled Back to NFL/MLB/EPL games control. Direct match links infer the sport from the loaded league.

Upcoming cards request the existing public match-market API and display only verified model-derived odds. EPL has home/draw/away; NFL and MLB have home/away. Browsing does not place a bet. Prices are still checked at acceptance in the match slip.

In-progress cards omit provider score snapshots. They show stored pregame odds when a model quote exists, clearly marked as closed. If no model quote exists, they show Model odds unavailable. No in-play model, live score feed or new post-kickoff betting has been added. Completed games retain final scores and link to results/replay.

Verified in the browser: EPL first page contains 12 games with date groups and different model prices; second page contains eight games; opening match 160 and clicking Back to EPL games returns to page 2. In-progress NFL cards omit scores and honestly show unavailable odds when no earlier model quote was saved. Frontend lint and production build pass.

Screenshots: docs/evidence/organized-odds-board.jpg and docs/evidence/contextual-back-button.jpg. The broader model/betting/parlay implementation and backend verification are documented in backend/docs/model_priced_odds.md and backend/docs/parlays_and_account_pages.md.


## Matchday, visual refresh, reset and sharing follow-up

The default is now Matchday: recent in-progress games lead, followed by all remaining games on the user's current local date (including completed games), then future scheduled games. Ordering happens before pagination. Local midnight boundaries are sent with timezone offsets; daylight-saving days are supported. In-progress records older than the previous local day are excluded. Historical results remain available under Final. Switching sports returns to Matchday; explicit status/search/page links still preserve their state. A client guard rejects obsolete server responses containing historical Matchday records instead of displaying old games as current.

Matchday requires the updated backend to be restarted along with the frontend. During development an older running server ignored the new query and returned 2023 history; restarting loaded the correction. Browser verification then showed November 15, 2026 NFL games under In progress and Today. The normal match endpoint remains backward compatible.

Navigation now uses balanced icon tabs. Blue/purple stadium lighting, subtle grid texture, sport colors and warm in-progress accents provide contrast without image assets or animation.

Wallet activity includes Reset demo wallet & bets. The user must check the confirmation box and confirm before it restores 1,000 points and permanently removes only that user's single/parlay tickets and prior wallet activity. Pending tickets cannot later settle because their records are removed. Account/login, other users, public fixtures and models remain intact. No new schema is required. POST /wallet/demo-reset requires an active session, CSRF, request_key and confirmation=RESET; foreign user fields are rejected. Reset receipts are retained internally for retry protection; only the latest round is visible in the ledger. Match/parlay/wallet locks follow settlement order, and a changed ticket set causes a retry before removal. Reset versus real settlement is covered by an isolated PostgreSQL concurrency check.

Share bet / Share parlay copies a plain-text summary of picks, accepted odds, stake, original potential return, leg status and ticket status. It contains no account email, session token or password. A manual-copy fallback appears when the browser clipboard is unavailable. This is a summary the user can paste into a message, not a public link to a private account or an automatically sent message.

Browser checks copied an existing parlay summary and verified reset confirmation is initially disabled. The existing demonstration account was not reset. Actual reset, retry, ownership and settlement behavior was exercised using isolated test users/databases. Additional screenshots are in docs/evidence/colorful-matchday-navigation.jpg, docs/evidence/today-first-games.jpg and docs/evidence/reset-wallet-confirmation.jpg.


## Closed-game odds follow-up

In-progress fixtures without a saved quote now receive a display-only reconstruction from the trained market model and prior-UTC-day feature history. The model training cutoff is checked against that target date. Current scores are not features. These are labeled Reconstructed pregame model odds, never live/in-play odds or a claim of a quote recorded before kickoff. Saved pregame prices are preferred when present.

This also covers started fixtures that never had a betting market: their preview has null market/outcome IDs, no market/quote/outcome records are inserted or changed, and betting remains closed. Missing/incompatible/later-trained models still show no estimate. Browser checks verified all seven in-progress NFL games: match 58 home 2.10 / away 1.74, match 60 home 1.65 / away 2.25. These figures depend on the configured model version.

MLB's empty Matchday view explicitly says No MLB games today, in progress, or coming up and links to completed games. Upcoming and In progress filters have their own specific empty-state wording. This describes the available imported schedule rather than claiming games never exist.

Full backend run after matchday/reset work: 640 passed, 69 skipped. Subsequent closed-odds focused checks include unchanged stored prices/quote counts, missing-market read-only previews, kickoff betting denial and rejection of models trained after a target game. Frontend build/lint and the MLB/odds browser checks passed. Screenshots: docs/evidence/in-progress-model-odds.jpg and docs/evidence/mlb-empty-schedule.jpg.
