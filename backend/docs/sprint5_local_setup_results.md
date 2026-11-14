# Local PostgreSQL setup results — November 13, 2026

Status: approved local schema setup and live virtual-betting workflow completed. Full PostgreSQL regression results are recorded below.

## A. Identity and backup

Verified `sports_betting`, configured at `localhost:5432`, connected through IPv6 loopback. Server: local Homebrew PostgreSQL 17.11. The PostgreSQL listener is owned by the local macOS user and bound to loopback. This matches the local development database authorized by the user; no remote destination was used.

Backup: `build/local-db-backups/20261113-183744/sports_betting-before-sprint5.dump` (43,860 bytes). `pg_dump`, `pg_restore --list`, and `pg_restore --file /dev/null` all exited 0. SHA-256: `450951713fa387c4be4b00f855fbdb74141ff4759f2408e90e44e8b15c596d3f`. Archive structure and complete SQL extraction were verified; a restore-to-database drill was not performed. Backup folder mode 0700, archive mode 0600, excluded by Git ignore rules. Adjacent verification JSON contains baseline counts and record fingerprints.

## B. Schema

Reviewed the entire SQL preview and setup code before applying. Created nine missing tables:

- `auth_sessions`
- `auth_csrf_challenges`
- `auth_login_attempts`
- `auth_assessment_records`
- `virtual_wallets`
- `demo_markets`
- `demo_outcomes`
- `virtual_bets`
- `virtual_wallet_transactions`

The setup also created associated sequences, primary/unique/foreign-key/check constraints and indexes. All nine tables exist, every new PostgreSQL constraint is validated, and no new invalid indexes were found. The schema verification JSON is adjacent to the backup. All existing table record fingerprints matched immediately after setup. No existing table was altered, dropped or truncated.

## C. Seed data

Inserted only three new synthetic matches: EPL ID 1, NFL ID 2, MLB ID 3. EPL 1 was subsequently completed by the authorized settlement test; NFL 2 and MLB 3 remain scheduled. Created three demo markets and seven outcomes, each with synthetic decimal odds 2.5000. Existing sports (5), leagues (5), and teams (30) were reused without changes. The authorized HTTP workflow subsequently created one synthetic user, one wallet, one bet and three wallet ledger records.

## D. HTTP checks

Restarted the real backend on port 8000 with `LOCAL_DEMO_HTTP=true VIRTUAL_BETTING_ENABLED=true`. Through the live Vite `/api` proxy, verified HTTP 200 for health, sports, leagues, teams, matches, match history, match detail, Swagger and OpenAPI.

Registration initially exposed a missing `users.password_hash` column. Work paused and the user explicitly approved the correction. Immediately before execution, the backup checksum and full-read verification were rechecked, the loopback database identity was verified, the users table was locked and confirmed empty, and column absence was confirmed. Applied exactly:

```sql
ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NOT NULL;
```

No users table recreation, default credentials, or existing-row changes were required. The initial failed registration inserted no records.

The live HTTP workflow through the frontend proxy then passed: register a synthetic account, login with CSRF, wallet balance 1,000, retrieve match 1 and PostgreSQL demo odds 2.5000, place 100-point bet, verify balance 900, retrieve pending bet, and repeat placement without another deduction. CLI settlement (`3–1` home win) marked the bet WON and credited 250 points, producing balance 1,150. Repeated settlement processed zero bets; the balance stayed 1,150 with exactly three ledger entries (initial credit, stake, payout).

The actual Uvicorn process was stopped and restarted. Using the saved session over HTTP against the fresh process verified the same user, wallet balance 1,150, WON bet and ledger. Read-only PostgreSQL checks confirmed the account uses a bcrypt hash, without exposing it. HTTP evidence: `build/sprint5-local-verification.json`.

Prediction route checks exposed existing limitations: `POST /predictions` returns 500 during missing-model registry initialization; `POST /predictions/matches/1` returns 422 because neither team has completed history. No frontend or ML source was changed.

## E. PostgreSQL persistence and concurrency

Development database: `sports_betting`. Isolated test database: `sportsbetting_sprint5_test`, both local at port 5432. The test database was created only after explicit approval and initialized with the base schema plus auth and betting tables (22 tables total). Development data was not copied. Tests use unique temporary schemas only within the test database; cleanup never targets the development database. Credentials were passed in child-process environments, not written to tracked files or printed.

Real backend restart persistence passed for the user, stored session, wallet and bet. PostgreSQL tests exercise wallet/bet transactions and concurrent duplicate-key retries versus competing stakes. Their final results appear below.

## F. Automated tests

Final full backend suite with Sprint 5 PostgreSQL integration enabled: **510 passed, 0 failed, 62 skipped**, 156 existing deprecation warnings, 82.13 seconds. JUnit: `build/sprint5-complete-tests.xml`.

Separate localhost HTTP mode tests: **2 passed, 0 failed, 96 deselected**, covering SQLite and PostgreSQL. JUnit: `build/sprint5-http-tests.xml`.

Both PostgreSQL concurrency cases passed: simultaneous identical requests create one bet/deduction; competing 600-point bets on a 1,000-point wallet allow only one and leave 400 points. The live development HTTP workflow additionally verified duplicate settlement and process-restart persistence.

Full-suite skip breakdown:

- 52: Existing Sprint 4 tests require their separately named disposable PostgreSQL database/configuration. Their SQLite variants passed; the Sprint 5 database was not substituted in violation of their guards.
- 4: Historical-import tests require their separately authorized disposable database/configuration.
- 1: Security PostgreSQL module requires its separate isolated security-test database/configuration.
- 2: Concurrency tests are inapplicable to SQLite row locking; both PostgreSQL counterparts passed.
- 1: SQLite-specific fault-injection trigger is inapplicable to PostgreSQL; the SQLite counterpart passed.
- 2: HTTP-mode cases are skipped in the default HTTPS suite and were both run successfully in the separate HTTP-mode invocation.

The initial PostgreSQL run found one fixture-only failure: explicitly inserted fixture IDs did not advance the demo market/outcome sequences. Corrected sequence initialization only inside isolated test fixtures; the complete rerun passed. No development sequences were reset.

## G. State and blockers

Feature branch remains `member3/sprint5-backend-virtual-betting`. No commits, pushes, merges, frontend edits or ML edits were made. Existing reference records were verified unchanged after setup and testing. The originally empty users and matches tables contain only the specifically authorized demo records. Backend and frontend are left running. Do not rerun the demo seed: it creates new records each time.

The missing password-hash column was corrected with explicit approval. Remaining blockers concern the existing ML prediction configuration and prototype frontend UI; virtual-point backend betting passed the live workflow.

## H. Access and startup

- Dashboard: http://127.0.0.1:5173/dashboard
- Frontend entry: http://127.0.0.1:5173/
- Backend: http://127.0.0.1:8000
- Health: http://127.0.0.1:8000/health
- Swagger: http://127.0.0.1:8000/docs
- OpenAPI: http://127.0.0.1:8000/openapi.json

From repository root, separate terminals:

```bash
cd backend
LOCAL_DEMO_HTTP=true VIRTUAL_BETTING_ENABLED=true ./venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```bash
cd frontend
npm run dev -- --host 127.0.0.1
```

The current frontend login screen remains a prototype; use the direct dashboard link. NFL and MLB synthetic schedules remain visible; no live sports feed or trained prediction artifacts were added.
