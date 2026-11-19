# Run VIGOR on Windows or macOS

This is the current fresh-install guide for the real-data betting app. Each person runs their own database, accounts and bets. GitHub supplies source code, not Andrew's `.env`, PostgreSQL installation/database, downloaded provider files, `node_modules`, virtual environment or trained models. Those must be created locally.

`Start-LocalApp.ps1` is an older Windows-only launcher for Andrew's private `build/postgres-runtime` and `build/postgres-data` layout. It does not install or initialize those files, which are ignored by Git. For a teammate install use **Run-LocalApp.py** after the setup below. It uses the Python environment you invoke, starts the backend/frontend on loopback, and leaves PostgreSQL under your normal OS/service management.

## 1. Get the right code

Use Git (not a ZIP) so updates are repeatable:

```text
git clone https://github.com/KamiloR7/SportsBetting_491.git
cd SportsBetting_491
```

For an existing checkout, first commit/stash your own work, then `git switch main` and `git pull --ff-only`.

This guide, launcher, complete NFL reference seeder and ML evaluation are included in PR #54 / branch `andrew/ml-evaluation-dashboard`. Until it merges, run the following from your cloned repository to get the PR version rather than main:

```text
git fetch origin
git switch andrew/ml-evaluation-dashboard
git pull --ff-only
```

Commit or stash your own changes before switching. After PR #54 merges, a current main checkout includes these files; the PR branch is then unnecessary.

## 2. Install prerequisites once

- **Python 3.12**, matching the backend CI version. Install an interpreter appropriate for your OS/CPU. On Mac use the macOS interpreter, not a copied Windows `.venv`.
- **Node.js 22.12 or newer in the 22.x line**, matching frontend CI. Vite's engine requires `^20.19.0 || >=22.12.0`; older Node 18/early 20 will fail.
- **PostgreSQL 17**, running locally, including `psql` command-line tools. A database already supplied by a teammate's own PostgreSQL install can be used if it is compatible; don't overwrite its existing tables with the fresh-schema step.
- **Git**, an internet connection, and a modern browser.

Official installers/documentation: [Python](https://www.python.org/downloads/), [Node.js](https://nodejs.org/en/download), [PostgreSQL Windows/macOS](https://www.postgresql.org/download/), [Vite Node requirements](https://vite.dev/guide/), [Python virtual environments](https://docs.python.org/3/library/venv.html).

Windows: start PostgreSQL through Services or the installed PostgreSQL tools. Add its `bin` directory to PATH if `psql` is not recognized; a common location is `C:\Program Files\PostgreSQL\17\bin`. If using a different version/location, use that actual directory.

Mac: use the service controls provided by your PostgreSQL installer. If installed through Homebrew, `brew services start postgresql@17`; add `$(brew --prefix postgresql@17)/bin` to PATH if needed. Homebrew normally uses your macOS username as the initial admin role, not necessarily `postgres`.

Check in a fresh terminal:

```text
node --version
npm --version
psql --version
```

Check Python with `py -3.12 --version` on Windows or `python3.12 --version` on Mac. Stop here and fix missing commands before continuing.

## 3. Create your Python environment and install dependencies

Start at the repository root. PowerShell commands (Windows):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -c backend/requirements-sprint2-tested.txt -r backend/requirements.txt
.\.venv\Scripts\python.exe -m pip install tzdata
Copy-Item backend/.env.example backend/.env
npm --prefix frontend ci
```

macOS Terminal:

```bash
python3.12 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -c backend/requirements-sprint2-tested.txt -r backend/requirements.txt
./.venv/bin/python -m pip install tzdata
cp backend/.env.example backend/.env
npm --prefix frontend ci
```

The constraints file is the one used in CI. `tzdata` supplies the IANA timezone database needed by historical NFL imports, particularly on Windows. These commands use the virtual environment directly, so PowerShell activation/execution-policy changes are unnecessary. Do not copy another person's environment folder or model pickle; train models with your installed dependencies.

Do not repeat the `.env` copy over an existing private file; edit it instead.

## 4. Create a fresh, separate database

These steps are for a **new empty local database**, not a migration of an existing account database.

Open an admin SQL terminal. On Windows this is usually:

```text
psql -U postgres -d postgres
```

On a Homebrew Mac, usually:

```text
psql postgres
```

If your installer supplied a different admin role, use it. Enter the following **inside psql**, choosing your own password when prompted:

```sql
CREATE ROLE vigor_local WITH LOGIN;
\password vigor_local
CREATE DATABASE sports_betting_local OWNER vigor_local;
\q
```

For this app's current unescaped database connection string, use a long letters-and-numbers local DB password; punctuation such as `@`, `/` or `#` can be misparsed. This is the database password, not a website account password. If the role or database already exists, inspect it instead of dropping it or rerunning CREATE blindly.

Back in your normal terminal at repository root:

```text
psql -h 127.0.0.1 -U vigor_local -d sports_betting_local -v ON_ERROR_STOP=1 -f backend/app/database/sports_prediction_schema.sql
```

This is the actual checked-in schema path. It creates tables and is not safe to rerun on a populated database. `relation already exists` means stop and inspect that database. Never drop your team's database to make this command pass.

## 5. Set backend/.env

Edit your private `backend/.env` to use these values, replacing the password placeholder:

```dotenv
DATABASE_HOST=127.0.0.1
DATABASE_PORT=5432
DATABASE_NAME=sports_betting_local
DATABASE_USER=vigor_local
DATABASE_PASSWORD=YOUR_OWN_LOCAL_DB_PASSWORD
MODEL_DIRECTORY=../build/sprint2-models
MARKET_MODEL_DIRECTORY=../build/market-models
LOCAL_DEMO_HTTP=true
VIRTUAL_BETTING_ENABLED=true
MODEL_ODDS_ENABLED=true
MODEL_ODDS_MARGIN=0.05
PARLAYS_ENABLED=true
AUTH_ASSESSMENT_ENABLED=false
AUTO_REFRESH_ENABLED=false
AUTO_REFRESH_INTERVAL_SECONDS=120
```

Run backend commands from **backend/** so `.env` and relative paths resolve consistently. The shared launcher does this for you. Keep both services on `127.0.0.1`; LOCAL_DEMO_HTTP is only for the local HTTP demonstration. Do not set VITE_API_URL to the backend URL: the default `/api` Vite proxy handles same-origin sessions and CSRF. Leave `frontend/.env` absent unless you understand its overrides.

Do not commit `.env`. Website accounts are created later through Create account; you do not receive Andrew's accounts by cloning.

## 6. Set up auth/betting, real history and models

Change into backend:

```text
cd backend
```

Run one command at a time, stopping at the first error. Use the block for your OS. Both run from **backend/**; the environment does not need to be activated.

Windows PowerShell:

```powershell
..\.venv\Scripts\python.exe -m app.database.seed_data
..\.venv\Scripts\python.exe -m app.database.seed_nfl_catalog
..\.venv\Scripts\python.exe -m app.database.virtual_betting_cli setup
..\.venv\Scripts\python.exe -m app.database.setup_model_odds
..\.venv\Scripts\python.exe -m app.database.setup_parlays
..\.venv\Scripts\python.exe -c "from pathlib import Path; Path('../build').mkdir(exist_ok=True)"
..\.venv\Scripts\python.exe -m app.ml.features.download_multisport_data --output ../data/raw
..\.venv\Scripts\python.exe -m app.database.import_real_history
..\.venv\Scripts\python.exe -m app.ml.train_market_models
..\.venv\Scripts\python.exe -m app.ml.evaluation.market_audit
..\.venv\Scripts\python.exe -m app.database.refresh_real_matches --days-back 2 --days-ahead 14 --output ../build/real-fixtures.json --apply
```

macOS Terminal:

```bash
../.venv/bin/python -m app.database.seed_data
../.venv/bin/python -m app.database.seed_nfl_catalog
../.venv/bin/python -m app.database.virtual_betting_cli setup
../.venv/bin/python -m app.database.setup_model_odds
../.venv/bin/python -m app.database.setup_parlays
../.venv/bin/python -c "from pathlib import Path; Path('../build').mkdir(exist_ok=True)"
../.venv/bin/python -m app.ml.features.download_multisport_data --output ../data/raw
../.venv/bin/python -m app.database.import_real_history
../.venv/bin/python -m app.ml.train_market_models
../.venv/bin/python -m app.ml.evaluation.market_audit
../.venv/bin/python -m app.database.refresh_real_matches --days-back 2 --days-ahead 14 --output ../build/real-fixtures.json --apply
```

`seed_data` creates reference sports/leagues, not match fixtures. The additional catalogue step ensures all 32 NFL team mappings exist even on a fresh offseason install; the older seed only includes six NFL teams. Historical import validates downloaded source hashes and creates real fixtures. Training writes your own market-model manifest and artifacts. The audit command requires the ML changes from PR #54; if deliberately using a version without that module, omit it and expect no detailed evaluation dashboard. Skip no earlier setup steps.

First-time downloads/training need time and provider access. Data counts, match IDs, prices and measured accuracy may differ by download date. The import does not use synthetic demo matches. Do not run `seed-dev-matches`, `seed-demo` or `auth_demo` to populate this real-data setup.

With the app still stopped, you may enable `AUTO_REFRESH_ENABLED=true` after setup if you want provider results checked every two minutes while the backend runs. Model retraining and history downloads remain explicit commands. If retraining later, regenerate the audit immediately afterward; a stale report is rejected.

## 7. Start the site on later visits

Start PostgreSQL first. Open a terminal at repository root, then use:

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe Run-LocalApp.py --check
.\.venv\Scripts\python.exe Run-LocalApp.py
```

macOS Terminal:

```bash
./.venv/bin/python Run-LocalApp.py --check
./.venv/bin/python Run-LocalApp.py
```

The basic check verifies prerequisites/port availability/database reachability, **not** database credentials, schema or trained models. Read the backend log messages if startup fails. The launcher installs nothing, imports no data, creates no database and never kills a process already using a port. Keep its terminal open. If either app service exits, it stops the other one. Ctrl+C stops both launched services and preserves data; PostgreSQL is managed separately by your OS. It does not run automatically when the computer starts.

Open **http://127.0.0.1:5173/dashboard**, then **Sign in / Join → Create account**. Register a new email/password; successful registration logs you in and starts a 1,000-point virtual wallet. There are no shared universal demo credentials. Existing accounts, bets and wallet activity belong to the local database you configured.

## Manual fallback: two terminals

If the Python launcher itself has an issue, you can run the exact underlying services. Keep both terminals open.

Backend terminal, from `backend/`:

```text
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Use the environment interpreter as in step 6. Frontend terminal, from repository root:

```text
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Stop each with Ctrl+C. Do not expose PostgreSQL or use `--host 0.0.0.0` to solve a local setup problem.

## Checks and common fixes

| Symptom/check | What to do |
|---|---|
| `Start-LocalApp.ps1` says database not initialized / pg_ctl missing | It expects Andrew's ignored Windows database directory. Use this guide and Run-LocalApp.py. Copying that script alone cannot supply a database. |
| Backend `http://127.0.0.1:8000/health` | Expect `status: ok`; this alone does not verify schema/model readiness. |
| `http://127.0.0.1:8000/leagues` | Expect JSON including NFL/MLB/EPL after reference seeding. |
| Backend unreachable / connection refused | Start local PostgreSQL, check DB host/port and read backend terminal errors. |
| password authentication failed | Confirm role/database/password with `psql -h 127.0.0.1 -U vigor_local -d sports_betting_local`; fix private .env and restart backend. |
| Missing tables / incompatible users schema | Apply the current base schema only to a new empty database, then additive setup. Existing databases need a reviewed migration. |
| `No module named ...` | Use the same .venv interpreter for installs, setup and startup. Run backend modules from backend/. |
| Node engine / Vite error | Verify Node version, then rerun `npm --prefix frontend ci`; don't copy Windows node_modules to Mac. |
| `Unmapped NFL team` on a fresh install | Run the complete NFL catalogue seed before historical import. If it reports a conflict on an old DB, inspect mappings rather than overwriting them. |
| No odds/model unavailable | Verify `../build/market-models/manifest.json`, train models using this DB and environment, restart backend. Avoid copying pickles across OS/dependency versions. |
| Detailed evaluation unavailable | Run market_audit after model training on a version containing PR #54. It refuses to pretend changed results match an old snapshot. |
| Source download/refresh fails | Stop at the failed command. Check connection/provider availability, then retry; do not continue training with missing files or invent fixtures. |
| MLB has no upcoming games | May be an offseason/provider schedule limitation. Use completed-game view to inspect history; not a launcher failure. |
| Login/CSRF/cookie trouble | Use exactly 127.0.0.1:5173 with the Vite /api proxy and LOCAL_DEMO_HTTP=true; don't mix localhost and 127.0.0.1. |
| Port 8000 / 5173 already used | Close the previous app terminal, or identify the other process. Launcher refuses to kill it automatically. |

## Validation boundary

The instructions were traced against the committed schema, CLI entry points, CI Python/Node versions, Vite proxy, ignored artifacts and model configuration. Four offline checks passed: complete/idempotent 32-team insertion, conflicting-mapping preservation, missing-prerequisite diagnostics, and cleanup of only the launcher-owned child processes. Prerequisite-only mode correctly reported missing .env/dependencies in the review checkout without starting services. The shared launcher has prerequisite-only mode and uses Python/Node subprocesses instead of Windows-specific executables.

A fresh macOS installation has **not** been executed here. No claim is made that a clean Mac/Windows end-to-end data download/training was tested on another person's machine. Have one Windows teammate and one Mac teammate follow these steps and report the first failing command/message (without passwords). Until PR #54 merges, teammates should use its branch as shown above; main does not include unmerged PR changes.
