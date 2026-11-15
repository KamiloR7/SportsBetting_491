# Backend integration readiness

This is a localhost-only university demonstration using integer virtual points with no cash value. It supplies no payment, deposit, withdrawal or real-money functionality. Frontend, ML and sports-data retrieval implementation remain with their respective teammates.

## Dependency and review boundary

This preparation depends on virtual betting PR #51, including settlement fix `40b49fc`. While #51 is unmerged, do not open these changes against main with its commits duplicated. Prefer waiting for #51 to merge, then apply the readiness-only diff on `member3/sprint5-backend-integration-readiness` from updated main. An explicitly agreed stacked PR would instead target `member3/sprint5-backend-virtual-betting`. This readiness review is stacked against the betting branch and does not change #51. After #51 merges, retarget to main and verify that only the readiness files remain. A squash merge may require transplanting the readiness commit onto updated main before retargeting; review that history change separately.

## Clean clone: prerequisites and Python

Use Python 3.12 (the tested runtime), PostgreSQL 17, and PostgreSQL CLI tools (`createdb`, `psql`). The PostgreSQL service and an authorized local database role must already exist. Installation/service changes are owner actions; no application import or startup performs them.

From the repository root:

```bash
python3 -m venv backend/venv
source backend/venv/bin/activate
python -m pip install -r backend/requirements.txt
```

Dependencies are declared in the repository; no extra runtime package is added by this readiness change. npm is only needed to run the existing frontend separately. Do not commit the virtual environment or dependency folders.

## Fresh PostgreSQL database

Use a new local database, such as `sports_betting_demo`, rather than a teammate's populated database. The sample commands use the existing local `postgres` role; select your authorized role if different. Enter credentials privately when prompted, never in Git or command-line URLs.

```bash
createdb --host=localhost --port=5432 --username=postgres sports_betting_demo
psql --host=localhost --port=5432 --username=postgres --dbname=sports_betting_demo --set=ON_ERROR_STOP=1 --file=backend/app/database/sports_prediction_schema.sql
```

Run the base SQL **once on a fresh database**. It contains its own BEGIN/COMMIT and is not an idempotent migration. If database creation fails because the name exists, stop and inspect the intended target; do not drop/recreate it or blindly load base SQL. Existing databases require a backup, ownership approval and schema inspection first.

Only on a fresh clone without an existing configuration file:

```bash
cp backend/.env.example backend/.env
```

Edit that ignored file locally. Required names are `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`. Set `DATABASE_NAME=sports_betting_demo` and use your own authorized account. Never overwrite another working `.env`. Pydantic settings read `.env` relative to the process working directory, so subsequent backend commands run from `backend/`.

Optional settings:

| Name | Default | Meaning |
|---|---|---|
| `LOCAL_DEMO_HTTP` | false | Permit authentication over loopback HTTP; select demo cookie policy at process startup |
| `VIRTUAL_BETTING_ENABLED` | false | Enable wallet, market and betting routes and registration wallet initialization |
| `AUTH_ASSESSMENT_ENABLED` | false | Enable the separate synthetic Sprint 4 assessment routes; not needed for ordinary betting |
| `MODEL_DIRECTORY` | `build/sprint2-models` | Artifact discovery for `POST /predictions`; relative paths resolve from the process directory |

Do not place arbitrary extra keys in the settings `.env`; undeclared settings may be rejected. `PREDICTION_MODEL_DIR` is a separate process-environment override read by the match-specific prediction helper, not a field in this `.env` settings model.

## Auth/betting tables and synthetic fixtures

After reviewing the selected local database configuration:

```bash
cd backend
./venv/bin/python -m app.database.virtual_betting_cli setup
./venv/bin/python -m app.database.seed_data
./venv/bin/python -m app.database.virtual_betting_cli seed-demo
```

`setup` validates the 13-table base schema and required users columns before creating anything. It creates the four auth and five virtual-betting tables in one transaction. Repeating compatible setup does not duplicate objects or create users/wallets. It does not repair arbitrary existing table definitions.

An old Sprint 1 users table may lack `password_hash VARCHAR(255) NOT NULL`. Setup rejects this before creating new auth objects. It does not invent hashes, add defaults or rewrite accounts. The earlier local upgrade had an empty users table and explicit owner approval for the column addition; populated legacy accounts need their own reviewed migration.

`seed_data` supplies the existing small sports/league/team reference set and is repeatable for compatible reference data. It is not a full real-world roster. `seed-demo` adds three synthetic scheduled fixtures, three markets and seven synthetic decimal-odds outcomes. Each invocation adds new fixtures, so run it once when preparing a demo. It does not download genuine games, seed users, train models or populate completed history. Current schema total is 22 tables.

## Start and verify

From `backend/`, with ports 8000/5173 available:

```bash
LOCAL_DEMO_HTTP=true VIRTUAL_BETTING_ENABLED=true ./venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- Backend: http://127.0.0.1:8000
- Health: http://127.0.0.1:8000/health
- Swagger: http://127.0.0.1:8000/docs
- OpenAPI: http://127.0.0.1:8000/openapi.json
- Expected backend root response: 404; no root page is defined.

Health confirms application availability, not database availability. Verify `/sports`, `/leagues`, `/teams`, `/matches` and `/matches/{id}/markets` separately. Match IDs come from the API/seed output; never assume they start at one. Restart the process after changing feature flags or cookie policy.

The existing frontend uses Vite at `http://127.0.0.1:5173` with `/api` proxied to port 8000. Keep the same loopback hostname throughout. Use that same-origin proxy for authentication and betting; arbitrary cross-origin requests/CORS are not configured. Frontend screens and service wiring remain teammate work.

## Frontend API contract

Full JSON schemas appear in Swagger and `sprint5_virtual_betting.md`. Decimal odds are JSON strings; points and stakes are integers. Never submit a user ID to choose ownership.

| Method and path | Request / requirements | Success |
|---|---|---|
| `POST /auth/register` | JSON email/password; optional username/display_name | 201, user fields only; 1,000-point wallet initialized atomically when betting enabled |
| `GET /auth/csrf` | Before login: create challenge cookie; after login: retrieve session CSRF token | 200, `csrf_token` |
| `POST /auth/login` | JSON email/password, challenge cookie, `X-CSRF-Token` | 200, user fields and session cookie |
| `GET /auth/me` | Session cookie | 200, current user |
| `POST /auth/logout` | Session cookie and authenticated CSRF header | 204, session revoked |
| `GET /wallet` | Session; betting enabled | 200, balance and `currency=virtual_points` |
| `GET /wallet/transactions` | Session; betting enabled | 200, own signed ledger entries |
| `POST /wallet/demo-topup` | JSON request_key; session and CSRF | 200, wallet after one 1,000-point refill per key |
| `GET /matches/{id}/markets` | Betting enabled; no authentication required | 200, market/outcome array; empty if no market |
| `POST /bets` | JSON match_id, outcome_id, stake, expected_odds, request_key; session and CSRF | 201, stored bet; identical retry returns original bet |
| `GET /bets` | Session | 200, own history, newest first |
| `GET /bets/{id}` | Session and ownership | 200, own bet; 404 for missing/other owner's bet |

Registration/login fields and examples are in the existing integration guide. A successful login consumes its pre-login challenge. Fetch `/auth/csrf` again after login and use the returned session token for mutations. Login returns no bearer token; do not store the session cookie manually in JavaScript. Browser same-origin fetch includes cookies. Logout before switching accounts.

Example bet body (illustrative IDs only; use IDs returned by your database):

```json
{"match_id":42,"outcome_id":11,"stake":100,"expected_odds":"2.5000","request_key":"browser-bet-unique-1"}
```

Use JSON content type. Preserve the key and payload on network retries; choose a new key for a deliberate new bet. A changed payload with the same key returns 409. Balance 1,000 becomes 900 after a 100-point stake; at accepted odds 2.5 a win credits 250 total, ending at 1,150. Loss leaves 900; void refunds the stake. Topup retries likewise reuse the original key.

Errors use `{"detail":"message"}` except ordinary schema validation's structured detail array. Auth validation is redacted. Expected statuses: 401 missing/invalid authentication; 403 transport/origin/CSRF; 404 unavailable/not owned; 409 conflict, closed betting, changed odds or insufficient points; 422 invalid input; 429 login throttle; 503 feature disabled or configured prediction service unavailable. Never count an empty market response as a usable betting market.

## ML handoff

Keep existing database match IDs and both endpoint contracts:

- `POST /predictions` with JSON `match_id` returns binary HOME_WIN/NOT_HOME_WIN probabilities, confidence, model version and history counts. Missing/ambiguous registry initialization now returns the same generic 503 as other unavailable-model failures; model paths are not exposed.
- `POST /predictions/matches/{id}` returns home/away probabilities and EPL draw handling; it requires a scheduled supported match, completed prior history for both teams and a trained artifact. Missing history returns 422; unavailable artifacts return 503.

The two response shapes are intentionally different; use the appropriate OpenAPI schema. No models are trained or supplied by setup. Paths are a common integration trap: `MODEL_DIRECTORY` is working-directory relative, while the match helper defaults to repository-root `build/sprint2-models`. If teammates supply artifacts there, use `MODEL_DIRECTORY=../build/sprint2-models` when running from backend and export `PREDICTION_MODEL_DIR=../build/sprint2-models` in the shell if overriding that helper. Compatible metadata/checksum files must accompany artifacts. Do not add that undeclared override to backend's settings `.env`.

This change does not resolve training quality, missing artifacts or insufficient history. No ML implementation is changed.

## Data Engineering handoff

Preserve internal match IDs across refreshes using provider mappings and the existing upsert services; never replace matches referenced by bets. Provider IDs are not internal IDs. Team/season references, source attribution and true timezone-aware starts are Data Engineering responsibilities. The historical CLI has an intentionally restricted import-only database target and is not a general development refresh command.

After an external writer marks a match final/cancelled, the operator still invokes settlement. The settlement fix in #51 accepts matching final scores or explicit void, locks and processes PENDING bets, leaves already-settled bets unchanged, closes markets and rejects conflicts. It does not automatically run on imported results and does not reverse corrected payouts.

```bash
./venv/bin/python -m app.database.virtual_betting_cli settle 42 --home-score 3 --away-score 1
./venv/bin/python -m app.database.virtual_betting_cli settle 43 --void
```

These are separate illustrative operator actions, not commands to run against arbitrary match IDs. EPL supports home/draw/away; NFL/MLB two-way ties void. Match results determine settlement; model predictions do not. Imported genuine matches do not automatically get markets. Demo odds must stay labeled synthetic even when the underlying match is genuine.

## Verification and limits

New focused tests load the real base SQL into unique schemas in the isolated local `sportsbetting_sprint5_test` database, call setup twice, verify all 22 tables, reject missing base/legacy accounts before writes, force transactional DDL failure, seed reference/demo data and exercise auth, wallet, markets, bet/history, externally finalized settlement, refill and logout contracts. A separate route test verifies sanitized model-initialization 503 handling. Existing settlement/concurrency and API regression tests remain in the full suite.

From repository root, after privately configuring `SPRINT5_TEST_DATABASE_URL` for that isolated database and setting `SPRINT5_ALLOW_DISPOSABLE_TEST=1`:

```bash
PYTHONPATH=backend backend/venv/bin/python -m pytest backend/tests/test_integration_readiness.py backend/tests/test_predictions_api.py -q -rs
PYTHONPATH=backend backend/venv/bin/python -m pytest backend/tests -q -rs
LOCAL_DEMO_HTTP=true PYTHONPATH=backend backend/venv/bin/python -m pytest backend/tests/test_virtual_betting.py -k local_http -q -rs
```

No connection string or credential belongs in Git. The test harness refuses development database names and cleans up only its random test schemas. The default full suite uses HTTPS test clients; run HTTP mode separately. Other existing PostgreSQL suites require their own guarded databases and remain skipped when not configured.

The clean-setup test verifies the SQL, setup CLI and seed functions against PostgreSQL; it is not an OS/package installation or GUI/browser walkthrough. Existing tests already cover repeated betting/settlement, ownership and PostgreSQL concurrency, so those are reused rather than copied into a new architecture. No scheduler, collector, frontend or ML model is introduced.
