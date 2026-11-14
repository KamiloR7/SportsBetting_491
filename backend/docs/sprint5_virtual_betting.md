# Sprint 5 virtual betting integration

Current local setup and verified workflow results: [local setup results](sprint5_local_setup_results.md). The preparation-stage status below predates the approved schema application and final PostgreSQL verification.

Local university demo only. Points have no cash value. Frontend UI and ML code are unchanged.

## Verification results

- Baseline before changes: 417 passed, 57 skipped.
- Final full backend suite: 463 passed, 109 skipped.
- Separate localhost HTTP flow: 1 passed, 1 PostgreSQL case skipped.
- `git diff --check`: clean.
- PostgreSQL table inventory inspected read-only; no database mutations performed.
- PostgreSQL-specific concurrency tests are implemented but not run because a disposable test database is not configured. No live Uvicorn process restart/persistence test was performed.

| Phase | Files / behavior | Database effect in existing development DB |
|---|---|---|
| Auth | `core/authentication.py`, `core/config.py`, `routes/auth.py`, `routes/auth_sessions.py`: reuse sessions/passwords, optional loopback HTTP, atomic initial wallet | None; new auth tables await approval |
| Wallet | `database/betting_tables.py`, `services/virtual_betting.py`, `routes/virtual_betting.py`: wallet, ledger, refill APIs | None; additive schema prepared |
| Matches/odds | `database/virtual_demo_fixtures.py`: explicit synthetic fixtures; market API | None; seed command not run |
| Bets | `services/virtual_betting.py`, `routes/virtual_betting.py`: transactional placement, retries, history, ownership | None; exercised only in disposable test fixtures |
| Settlement | `database/virtual_betting_cli.py`: local completion/void procedure | None; exercised only in disposable test fixtures |
| Verification | `tests/test_virtual_betting.py`, `tests/test_auth_policy.py`, `app/security_assessment.py`: workflow, rollback, access policies, optional PostgreSQL concurrency | None |

## Setup and current status

Use the existing backend virtual environment and PostgreSQL configuration. The feature is opt-in; no schema creation occurs at startup. The verified local setup now has 22 tables. Teammates must apply the additive setup to their own databases separately; Git changes do not migrate PostgreSQL. **Database-owner approval and a verified backup are required before setup against an existing database.**

After approval, from `backend/`:

```bash
./venv/bin/python -m app.database.virtual_betting_cli setup
```

The review-only SQL preview is `backend/docs/sprint5_virtual_betting_schema.sql`.

This creates missing `auth_sessions`, `auth_csrf_challenges`, `auth_login_attempts`, `auth_assessment_records`, `virtual_wallets`, `virtual_wallet_transactions`, `demo_markets`, `demo_outcomes`, and `virtual_bets`. It does not drop tables or change the existing users/matches schema. It does not reconcile incompatible pre-existing tables. Base project schema and reference sports/leagues/teams must already exist.

An older Sprint 1 database may lack `users.password_hash`, even though current base SQL includes it. The setup command creates missing tables only; it does not add this column automatically. Inspect the existing users schema first. For the verified local upgrade, the users table was empty and the owner explicitly approved `ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NOT NULL` after backup. Do not run that alteration blindly against populated or differently structured accounts; review an appropriate migration separately.

Start the backend with explicit demo flags, without editing `.env`:

```bash
LOCAL_DEMO_HTTP=true VIRTUAL_BETTING_ENABLED=true ./venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Default flags are false. Existing HTTPS authentication remains the default. HTTP mode permits authentication only for loopback hostnames; it uses non-Secure, HttpOnly, SameSite=strict cookies with unprefixed names. Bind only to loopback. Cookie policy is chosen at process startup, so restart when changing flags. Do not enable this demo mode for public hosting.

To insert isolated, **synthetic** scheduled matches with demo odds after approval:

```bash
./venv/bin/python -m app.database.virtual_betting_cli seed-demo
```

This adds three new fixtures, one each for EPL/NFL/MLB, using existing reference teams and start times seven days ahead. Each invocation creates new fixtures; do not repeatedly run it unless new fixtures are wanted. Returned match IDs identify the synthetic records. All odds are explicitly synthetic demo odds, never bookmaker quotes. The command is explicit and is not run on startup.

## URLs and authentication

API: `http://127.0.0.1:8000`; Swagger: `/docs`; OpenAPI: `/openapi.json`.

Existing Vite proxy: frontend `http://127.0.0.1:5173` requests `/api/...`. Use this same-origin proxy, with browser cookies, instead of cross-origin API calls. HTTP demo mode accepts the exact matching loopback frontend origin on port 5173. In production-default HTTPS mode the existing strict origin policy applies.

1. `POST /auth/register` body:
   `{"email":"student@example.com","password":"DemoPassword123!","username":"student"}`.
   Returns 201 with existing user schema (`id`, `email`, `username`, `display_name`, `is_active`, `created_at`). No password hash is returned. Duplicate account: 409. New wallets receive 1,000 points atomically when betting is enabled. Existing users receive one wallet lazily on wallet access/first operation.
2. `GET /auth/csrf` obtains `{"csrf_token":"..."}` and a temporary challenge cookie.
3. `POST /auth/login` body `{"email":"student@example.com","password":"DemoPassword123!"}`, header `X-CSRF-Token` from step 2. Returns the user and sets the session cookie. Wrong credentials: 401; repeated failures: 429.
4. `GET /auth/csrf` again after login returns the authenticated session's CSRF token. Use this token for wallet topups, bet placement, and logout.
5. `GET /auth/me` returns the authenticated user. `POST /auth/logout` with the session CSRF header revokes the session (204).

Sessions persist in PostgreSQL for 30 minutes. Never supply a user ID to choose a wallet or bet owner. Switch accounts by logging out first.

## Wallet

| Method | Route | Body / response |
|---|---|---|
| GET | `/wallet` | `{"balance":1000,"currency":"virtual_points"}` |
| GET | `/wallet/transactions` | Array of `id,user_id,amount,kind,reference,created_at` |
| POST | `/wallet/demo-topup` | `{"request_key":"refill-unique-1"}`; adds 1,000 points once per user/key; returns wallet |

Authenticated session required. POST also requires CSRF. Transaction kinds: `INITIAL`, `DEMO_TOPUP`, `STAKE`, `PAYOUT`, `REFUND`. Positive ledger amounts credit points; negative amounts deduct points. Reuse the exact request key for network retries. Each deliberate new refill uses a new key. Demo balance cap is enforced. All balances and stakes are integers.

## Matches and markets

Existing `/sports`, `/leagues`, `/teams`, `/matches?league_id=...&status=scheduled`, `/matches/{id}`, and `/matches/history` contracts remain unchanged.

`GET /matches/{id}/markets` returns an array (empty when no market is configured):

```json
[{
  "market_id": 1,
  "match_id": 42,
  "market": "single_match_winner",
  "odds_source": "synthetic_demo",
  "is_open": true,
  "outcomes": [
    {"id": 11, "selection": "home", "decimal_odds": "2.5000"},
    {"id": 12, "selection": "away", "decimal_odds": "2.5000"},
    {"id": 13, "selection": "draw", "decimal_odds": "2.5000"}
  ]
}]
```

Draw is supported only for EPL. NFL and MLB use home/away. Placement rejects matches that have started, are not scheduled, or have a closed/missing market. `is_open` is the stored market switch; frontend should also check match status/time, and placement always revalidates eligibility.

## Place and retrieve bets

`POST /bets` requires session + CSRF and JSON content type:

```json
{"match_id":42,"outcome_id":11,"stake":100,"expected_odds":"2.5000","request_key":"bet-unique-1"}
```

Returns 201:

```json
{
  "id":1,"user_id":1,"match_id":42,"outcome_id":11,"selection":"home",
  "stake":100,"accepted_odds":"2.5000","potential_payout":250,
  "status":"PENDING","request_key":"bet-unique-1","created_at":"2026-11-13T20:00:00Z"
}
```

Stake range: 1–1,000,000 integer points. Decimal odds must be greater than 1 and at most 1,000 (up to four fractional digits). The backend verifies expected odds against stored odds and snapshots accepted odds. Total winning credit includes the stake and is `floor(stake * accepted_odds)`. Wallet deduction and bet creation are committed together. Starting balance 1,000 becomes 900 after a 100-point bet; a 2.5 winning bet ends at 1,150. Loss ends at 900; void ends at 1,000.

Retries with the same user/key and identical payload return the original bet without another deduction, including after settlement. Reusing a key for different payload returns 409. Wallet and match row locks serialize PostgreSQL operations.

`GET /bets`: current user's history, newest first.
`GET /bets/{bet_id}`: current user's single bet; missing/other-owner returns 404.
Statuses: `PENDING`, `WON`, `LOST`, `VOID`.

## Settlement: local operator only

There is deliberately no settlement HTTP endpoint. After reviewing the synthetic match ID, the local operator runs:

```bash
./venv/bin/python -m app.database.virtual_betting_cli settle 42 --home-score 3 --away-score 1
# Or cancel/refund:
./venv/bin/python -m app.database.virtual_betting_cli settle 42 --void
```

Completion stores final scores/status, closes the market, settles pending bets and updates wallets/ledger in one transaction. Identical repeated settlement does nothing; a conflicting replacement result is rejected. EPL ties settle draw bets; ties in two-way NFL/MLB markets void/refund all bets. Cancellation refunds original stakes. Do not use this demo mechanism to overwrite real results.

## Errors and ML compatibility

Errors use FastAPI `{"detail":"message"}`; normal schema errors use `{"detail":[...]}`. Authentication validation is redacted to `{"detail":"Invalid authentication request."}`. Statuses: 401 unauthenticated/invalid credentials; 403 CSRF/origin/transport; 404 missing/not owned; 409 duplicate account, insufficient points, closed match, changed odds, or request-key conflict; 422 invalid input; 429 login throttle; 503 betting feature disabled.

ML endpoints remain `POST /predictions` (`{"match_id":42}`) and `POST /predictions/matches/{id}`. Predictions refer to the same database match IDs; odds and bet settlement do not use model predictions. No ML training code was changed. Model artifacts and completed history are still required separately.

## Validation and limits

Run `PYTHONPATH=backend backend/venv/bin/python -m pytest backend/tests -q` from the repository root. New workflow tests use an isolated file-based SQLite database; they exercise real routes, password hashing, sessions, committed balances, and persistence after reconnecting with a fresh API client. They do not prove PostgreSQL concurrent locking or a live process restart. PostgreSQL test coverage requires explicit disposable-database configuration; existing development data is never used for mutation tests.

The local setup report records successful live HTTP betting and backend restart persistence after approved setup. Teammates must enable the opt-in routes after reviewing and applying setup to their own databases. Frontend wiring for wallet/bet UI is teammate work. No parlays, real money, external odds feed, automated results ingestion, or public deployment is included.

Optional PostgreSQL tests require a database owner to first provision an empty local database named `sportsbetting_sprint5_test`. Set `SPRINT5_TEST_DATABASE_URL` privately to its SQLAlchemy PostgreSQL URL and `SPRINT5_ALLOW_DISPOSABLE_TEST=1`, then run `backend/tests/test_virtual_betting.py`. The harness creates a unique schema for each test and removes only that test schema afterward. It refuses other database names and remote hosts. Do not point it at the development database. The optional tests include competing wallet deductions and simultaneous duplicate-request retries; they have not been run without this explicit setup.

The localhost HTTP path can be checked independently with:

```bash
LOCAL_DEMO_HTTP=true PYTHONPATH=backend backend/venv/bin/python -m pytest backend/tests/test_virtual_betting.py -k local_http -q
```

Default HTTPS security tests remain part of the full suite; do not run that full suite with HTTP demo mode enabled.
