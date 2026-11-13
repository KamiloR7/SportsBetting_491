# Sprint 4 authentication and access assessment

Dang Nguyen owns CC6.1 backend enforcement for the synthetic assessment. This
extends the existing FastAPI registration and bcrypt implementation. It does
not implement a production sports-data backend, private prediction history,
the React login integration, or SOC 2 certification.

## Work and ownership

| Parent | Retained subtasks | Deliverable |
| --- | --- | --- |
| SCRUM-180 | 186, 187, 188, 189, 190 | Route review, authentication, safeguards, ownership, documentation/review |
| SCRUM-191 | 199, 200, 201, 202 | Preserve CI, disposable PostgreSQL, schema setup, executed results |
| SCRUM-192 | 204, 205, 206, 207 | Positive/session, denial/safeguards, ownership/write integrity, evidence |
| SCRUM-281 | Acceptance checklist in parent | U1.1–U1.4 assessment, limitations and review |

Each parent has at most five subtasks. All IDs are existing Jira IDs. Ayman
reviews Dang; Dang reviews Kamilo under the group proposal. No review or merge
is implied by passing local tests.

## Implemented behavior

- `POST /auth/register`: existing public registration, now HTTPS-only, with
  case-normalized email, bcrypt's 72-byte input limit and duplicate-race handling.
- `GET /auth/csrf`: HTTPS, same-origin pre-login challenge. After login, returns
  the CSRF token bound to the current session. Responses use `Cache-Control: no-store`.
- `POST /auth/login`: valid pre-login CSRF and bcrypt credentials are required.
  Creates a fresh 256-bit opaque token, stores only its SHA-256 digest, and issues
  a `__Host-` cookie with Secure, HttpOnly, SameSite=Strict, Path=/ and 1800-second
  Max-Age. Session expiry is enforced by the backend, not just the cookie.
- `GET /auth/me`: valid session and active account required; response-model
  filtering excludes password hashes and session state.
- `POST /auth/logout`: requires the session-bound CSRF token and deletes the
  presented server-side session immediately. Other sessions are independent.
- `GET/PATCH /auth/assessment/records/{record_id}`: explicitly synthetic
  ownership/read/write examples. Disabled by default; the assessment enables
  them with `AUTH_ASSESSMENT_ENABLED=true`. PATCH requires CSRF. Both enforce
  owner identity on the server; rejections perform zero protected record writes.
- Five failed logins in a **rolling** five-minute window block the next attempt
  for 15 minutes from the fifth failure. The case-normalized account key and
  bounded timestamps live in PostgreSQL; a row lock serializes concurrent
  attempts. Successful login resets the count. Client forwarding headers do not
  choose the throttle key. Unknown and inactive accounts get generic errors.

The existing sport/team/match browsing, completed-match results and public
inference endpoints remain public. `/matches/history` is public match history,
not private account prediction history. `security_assessment.py` classifies all
24 actual HTTP method/route pairs, including generated docs; four are protected.
The policy test fails if a new route lacks an explicit classification or a
protected route lacks an authentication dependency and denial-test case.

## Reproduce the tests

Use Python 3.12 and a fresh virtual environment. From the repository root:

```sh
python -m venv .venv
.venv/bin/python -m pip install -c backend/requirements-sprint2-tested.txt -r backend/requirements.txt
.venv/bin/python -m pip install -e .
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests/test_auth_security.py backend/tests/test_auth_policy.py -v --junitxml=build/sprint4/auth-results.xml
PYTHONPATH=backend .venv/bin/python -m app.security_assessment
PYTHONPATH=backend .venv/bin/python -m app.security_tls_smoke
```

Without an explicitly configured disposable PostgreSQL database, PostgreSQL
cases skip. That is **not** a PostgreSQL pass. To require integration, provision
an empty local database named exactly `sportsbetting_sprint4_test` and set:

```sh
export SPRINT4_TEST_DATABASE_URL='postgresql+psycopg2://sprint4_test:disposable_ci_only@127.0.0.1:5432/sportsbetting_sprint4_test'
export SPRINT4_ALLOW_DISPOSABLE_TEST=1
export SPRINT4_REQUIRE_POSTGRES=1
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests/test_auth_security.py backend/tests/test_auth_policy.py -v --junitxml=build/sprint4/auth-results.xml
PYTHONPATH=backend .venv/bin/python -m pytest -q --junitxml=build/sprint4/regression.xml
```

The URL above is an example for the disposable CI service, not a production
credential. Only localhost/127.0.0.1/::1 and the exact disposable database name
are accepted. Every test creates a random schema, applies the existing base
DDL plus additive auth tables, then drops only that schema. Required database
configuration errors fail instead of silently skipping. No provider data or
shared developer/production database is needed.

The HTTPS smoke launches a temporary loopback Uvicorn server and synthetic
SQLite database. It generates and explicitly trusts a temporary test certificate,
checks cookies/CSRF/ownership/logout over real TLS, then stops the server and
removes the temporary key/certificate. It never uses `verify=False` or emits
passwords, cookies or tokens. Its SQLite result does not substitute for the
separate PostgreSQL tests.

## Schema setup and frontend handoff

The existing database's `users` table must be initialized first. After reviewing
the configured `DATABASE_*` values, the explicit additive command is:

```sh
PYTHONPATH=backend .venv/bin/python -m app.database.init_auth --apply
```

It creates `auth_sessions`, `auth_csrf_challenges`, `auth_login_attempts` and
`auth_assessment_records`. There is no schema migration or seed on normal app
startup. Tests and the explicit `app.database.auth_demo:app` entrypoint own only
their isolated schemas/data. Disable assessment routes outside the classroom.

Ayman's frontend should use a same-origin HTTPS API: fetch `/auth/csrf` with
cookies, submit its token in `X-CSRF-Token` on login, then fetch the session's new
CSRF token and send it on logout/protected writes. Do not store the session in
JavaScript or log credentials. Cross-origin deployment requires an agreed
trusted-origin/proxy/CORS design; it is intentionally not enabled here. The
existing React login still navigates as a UI prototype; the password console
log was removed, but full UI/session integration belongs to the frontend handoff.

## CI and evidence

The existing build metadata, pytest/coverage, ML smoke and frontend jobs are
preserved. The new `auth-security` job uses PostgreSQL 17, executes all security
cases with PostgreSQL required, runs the real HTTPS smoke, and uploads
`build/sprint4/` as `sprint4-auth-<commit>`. The main build's unconfigured
PostgreSQL cases can skip; the dedicated required-PostgreSQL run is the evidence
for this assessment. Review the actual hosted run, not merely the YAML.

Evidence and results are recorded in `ASSESSMENT.md` and `evidence/`. No human
review, merged-main run, frontend integration or production readiness should
be inferred from a local pass or from this implementation guide.

## Residual boundaries

The synthetic records demonstrate ownership; real private prediction history
is unimplemented. The local SQLite demo is for serial walkthroughs; concurrent
throttle verification uses PostgreSQL. Account lockout intentionally follows
the proposal and can be abused to deny a known account service; production
needs recovery and additional abuse controls. Challenge/unknown-account rows
need a production retention/traffic-limiting policy. MFA, reset/recovery,
deployment TLS/proxy configuration and monitoring ingestion are outside this
prototype. Legacy emails differing only by case fail login closed and need
account-data reconciliation before production integration.

Design references: [OWASP session management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
and [OWASP CSRF prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).
