# Game board and return navigation

November 15, 2026. The Explore board now requests 12 games per page instead of 30, groups them by local calendar day and uses compact cards with distinct sport accents. Page navigation remains server-paginated. Search, sport, status and offset are included in each match link and preserved by the styled Back to NFL/MLB/EPL games control. Direct match links infer the sport from the loaded league.

Upcoming cards request the existing public match-market API and display only verified model-derived odds. EPL has home/draw/away; NFL and MLB have home/away. Browsing does not place a bet. Prices are still checked at acceptance in the match slip.

In-progress cards omit provider score snapshots. They show stored pregame odds when a model quote exists, clearly marked as closed. If no model quote exists, they show Model odds unavailable. No in-play model, live score feed or new post-kickoff betting has been added. Completed games retain final scores and link to results/replay.

Verified in the browser: EPL first page contains 12 games with date groups and different model prices; second page contains eight games; opening match 160 and clicking Back to EPL games returns to page 2. In-progress NFL cards omit scores and honestly show unavailable odds when no earlier model quote was saved. Frontend lint and production build pass.

Screenshots: docs/evidence/organized-odds-board.jpg and docs/evidence/contextual-back-button.jpg. The broader model/betting/parlay implementation and backend verification are documented in backend/docs/model_priced_odds.md and backend/docs/parlays_and_account_pages.md.
