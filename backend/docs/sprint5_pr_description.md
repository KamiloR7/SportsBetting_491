# Summary

Add a PostgreSQL-backed virtual-points betting backend for the localhost CPSC 491 demonstration. Authenticated users can receive 1,000 starting points, browse synthetic EPL/NFL/MLB winner markets, place single-match bets, and retrieve their wallet and betting history. A local operator CLI settles results and credits payouts or refunds transactionally.

All betting uses simulated points with no cash value. Frontend UI and ML training/inference source are unchanged.

# Changes Made

- **Authentication and user accounts:** Reuse existing bcrypt registration and persistent session login, logout and account lookup. Initialize the wallet with registration when betting is enabled. Add explicit loopback HTTP demo mode while retaining HTTPS behavior by default; preserve CSRF and ownership checks.
- **PostgreSQL schema:** Provide explicit additive initialization for existing auth definitions and new betting tables. Application startup never runs schema setup automatically.
- **Virtual points wallets:** Add persistent balances, signed transaction history and repeat-safe 1,000-point demo refills. Prevent negative balances and keep balance-changing operations transactional.
- **EPL/NFL/MLB demo markets and odds:** Store synthetic winner markets and decimal odds in PostgreSQL. EPL supports home/draw/away; NFL and MLB support home/away. Provide an explicit synthetic-fixture CLI.
- **Bet placement and history:** Validate match eligibility, selected outcome, expected odds, integer stake and available points. Snapshot accepted odds and potential payout; commit bet, deduction and ledger together. Per-user request keys prevent duplicate bets/deductions and reject changed retry payloads. Restrict bet reads to their owner.
- **Settlement and payouts:** Local CLI only; no ordinary-user settlement endpoint. Support WON, LOST and VOID, payout/refund ledger entries, and repeat settlement without duplicate credit. NFL/MLB ties void two-way bets; EPL draws settle the draw outcome.
- **Automated testing:** Cover API/auth regressions, invalid bets, retry conflicts, ownership, rollback, settlement, persistence across connection recreation and PostgreSQL concurrency. Extend the explicit route access-policy inventory.
- **Documentation and handoff:** Include endpoint contracts, setup instructions, historical/current schema SQL, inventory, evolution notes, Mermaid ER/flow diagrams and verification evidence summaries.

# Database Changes

The Sprint 1 foundation contains 13 tables. The documented local Sprint 5 schema contains 22 tables, 138 columns and 26 foreign keys.

Four authentication tables were **defined in Sprint 4** and **created locally during Sprint 5 setup**:
`auth_sessions`, `auth_csrf_challenges`, `auth_login_attempts`, `auth_assessment_records`.

Five new Sprint 5 betting tables:
`virtual_wallets`, `virtual_wallet_transactions`, `demo_markets`, `demo_outcomes`, `virtual_bets`.

The older local `users` table also required `password_hash VARCHAR(255) NOT NULL`. That column was already defined in later source SQL, but was absent locally. It was added only after verifying an empty table, a completed backup and explicit owner approval. No existing table was dropped/recreated or records overwritten.

**Teammate setup is explicit:** review the schema and take a backup before running `python -m app.database.virtual_betting_cli setup` from `backend/`. This creates missing tables; it does not repair incompatible existing tables or automatically add the password column. Inspect older account schemas and review an appropriate migration separately. Run `seed-demo` only when synthetic fixtures are wanted; each invocation adds new fixtures.

Local database changes do not propagate through GitHub. Database credentials, backups, application data, generated test reports and environment files are excluded from this PR. Schema-only SQL files intentionally contain definitions, not records or sequence counters.

# Testing and Verification

**Fresh PR-preparation verification, November 13, 2026:**

- Full backend suite, including unit/API regression tests and isolated SQLite/PostgreSQL workflows: **510 passed, 0 failed, 62 skipped**. This includes **47 passing PostgreSQL betting cases**, with both concurrency cases passing.
- Separate localhost HTTP-mode tests on SQLite and PostgreSQL: **2 passed, 0 failed; 96 deselected**.
- Python compilation: **103 application/test files passed**.
- Git whitespace, intended-file hygiene, schema-only SQL and documentation completeness checks passed.
- Read-only development-schema comparison matched documented columns, primary/foreign keys, unique/CHECK constraints and indexes across all 22 tables. ER coverage includes all 22 tables, 138 columns and 26 physical FK edges.

The 62 full-suite skips are explicit: 52 existing Sprint 4 PostgreSQL cases require another guarded test database; four historical-import cases require a separate authorized database; one security PostgreSQL module requires its isolated configuration; two concurrency variants are inapplicable to SQLite; one fault-injection trigger is SQLite-only; two HTTP-mode variants were run successfully in the separate invocation. Skips are not counted as passes.

Current machine-readable results are generated locally as `build/sprint5-pr-tests.xml` and `build/sprint5-pr-http-tests.xml` and are intentionally not committed. Existing deprecation warnings remain.

**Historical live verification, not rerun during PR preparation:** registration/login through the frontend proxy; 1,000 starting points; a 100-point bet leaving 900; a 2.5-odds winning settlement ending at 1,150; duplicate placement/settlement without extra balance changes; and persisted user, session, wallet and bet after stopping and restarting Uvicorn. See `backend/docs/sprint5_local_setup_results.md`. Current automated persistence tests recreate connections/API clients; they are not a new live-process restart test.

# Frontend and ML Integration

Frontend interfaces:

- Existing `/auth/register`, `/auth/csrf`, `/auth/login`, `/auth/logout`, `/auth/me`.
- `GET /wallet`, `GET /wallet/transactions`, `POST /wallet/demo-topup`.
- `GET /matches/{match_id}/markets`.
- `POST /bets`, `GET /bets`, `GET /bets/{bet_id}`.

Use the existing Vite `/api` proxy, session cookies, JSON content type and the authenticated CSRF header for mutations. Send a stable request key for retries and the expected decimal odds when placing a bet. See `backend/docs/sprint5_virtual_betting.md` for full JSON contracts.

Existing sports, leagues, teams, matches/history and prediction interfaces are preserved. ML predictions associate with the same database match IDs; bets settle from match results, not predictions. The frontend login screen still needs actual authentication integration. Trained model artifacts and completed match history are still required; historical live checks found an unhandled missing-model 500 on `/predictions` and an insufficient-history 422 on the match prediction route.

# Known Limitations

- Synthetic fixtures and demo odds; no live bookmaker feed.
- Virtual points only: no real money, payments, deposits or withdrawals.
- Localhost educational use only; no production/public deployment.
- Single-match winner bets only; no parlays.
- Default feature flags are off. Local HTTP use requires `LOCAL_DEMO_HTTP=true VIRTUAL_BETTING_ENABLED=true` and a loopback-bound backend.
- Settlement is an explicit operator CLI procedure; results ingestion is not automatic.
- Some cross-table/settlement rules and ledger reconciliation are application-enforced rather than independent database constraints.
- No automatic migration of legacy populated account tables and no versioned migration ledger.
- Additional guarded PostgreSQL suites remain unconfigured; Mermaid source was structurally checked but visual rendering was not verified.

# Reviewer Checklist

- [ ] Review authentication, ownership, retry behavior, transaction boundaries and settlement logic.
- [ ] Review additive schema/setup requirements and legacy users-table migration guidance.
- [ ] Run backend tests and configured PostgreSQL/HTTP variants; review skips.
- [ ] Confirm frontend and ML API compatibility and documented integration gaps.
- [ ] Review API handoff, schema evolution, inventory and Mermaid diagrams.
- [ ] Confirm no secrets, environment files, database records/backups or generated local artifacts are included.
