# Sports Match Prediction — Backend

This directory contains the FastAPI backend for the CPSC 491 Sports Match Prediction application.

The backend is currently an **initial Sprint 1 scaffold**: the application, configuration, and database connection setup are in place, but API routes, ORM models, services, tests, and prediction functionality have not been implemented yet. These will be added incrementally in future sprints.

---

## Technology Stack

- **FastAPI** — web framework used to build the API
- **PostgreSQL** — relational database for storing sports, teams, matches, and predictions
- **SQLAlchemy** — Python SQL toolkit / ORM used to talk to PostgreSQL
- **Pydantic Settings** — loads and validates configuration from environment variables
- **Uvicorn** — ASGI server used to run the FastAPI app locally
- **Alembic** — planned for managing future database migrations
- **pytest / httpx** — planned for automated backend testing

---

## Machine-Level Prerequisites

Install these directly on your computer. They are **not** installed by `pip` and are separate from the Python packages listed in `requirements.txt`.

- [Git](https://git-scm.com/)
- Python 3
- [Homebrew](https://brew.sh/) (used for the macOS setup steps below)
- PostgreSQL 17
- [pgAdmin 4](https://www.pgadmin.org/) — optional, but recommended for visually browsing the database

Python packages such as FastAPI and SQLAlchemy should **not** be installed manually one at a time. They are declared in `backend/requirements.txt` and installed together in one step (see [First-Time Backend Setup](#first-time-backend-setup)).

---

## PostgreSQL Prerequisite

On macOS with Homebrew:

```bash
brew install postgresql@17
brew services start postgresql@17
pg_isready
```

`pg_isready` should report that PostgreSQL is accepting connections. If it doesn't, see [Troubleshooting](#troubleshooting).

This backend also requires a local `sports_betting` database with the project schema loaded. Full step-by-step instructions (including pgAdmin setup) are documented in:

```
backend/DATABASE_SETUP_README.md
```

At minimum, you must create the `sports_betting` database and load the schema from:

```
backend/app/database/sports_prediction_schema.sql
```

before any database-dependent backend functionality will work.

---

## First-Time Backend Setup

Run the following from the **repository root**:

```bash
python3 -m venv backend/venv
source backend/venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
```

What each command does:

1. `python3 -m venv backend/venv` — creates an isolated Python virtual environment inside `backend/venv`
2. `source backend/venv/bin/activate` — activates that virtual environment for your current terminal session
3. `pip install -r backend/requirements.txt` — installs all backend Python dependencies at once
4. `cp backend/.env.example backend/.env` — creates your personal local environment file from the committed example

---

## Environment Variables

After copying `.env.example` to `.env`, edit `backend/.env` with your own local PostgreSQL connection details:

```
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=sports_betting
DATABASE_USER=postgres
DATABASE_PASSWORD=your_local_password
```

Important notes:

- `.env.example` contains only placeholder values and **is safe to commit**.
- `backend/.env` contains your local configuration and **must not be committed**. It is already excluded via `.gitignore`.
- Database credentials must never be hard-coded into Python files — they are always read from environment variables via `app/core/config.py`.
- Each teammate will likely have different local PostgreSQL credentials, so `.env` is personal to your machine.

---

## Running FastAPI

From the repository root:

```bash
cd backend
uvicorn app.main:app --reload
```

A successful startup will print messages similar to:

```
Uvicorn running on http://127.0.0.1:8000
Application startup complete.
```

---

## Development URLs

While the server is running, the following are available:

```
API:          http://127.0.0.1:8000
Swagger Docs: http://127.0.0.1:8000/docs
OpenAPI JSON: http://127.0.0.1:8000/openapi.json
Health Check: http://127.0.0.1:8000/health
```

FastAPI automatically generates the interactive Swagger UI at `/docs` from the app's route definitions — no extra setup is required.

---

## Health Endpoint

The backend currently implements:

```
GET /health
```

Expected response:

```json
{
  "status": "ok"
}
```

This endpoint currently only confirms that the FastAPI server itself is running and responding to requests. It does **not** check PostgreSQL connectivity or any database state.

---

## Python Dependencies

```bash
pip install -r backend/requirements.txt
```

installs the dependencies currently declared in `backend/requirements.txt`:

- `fastapi`
- `uvicorn[standard]`
- `sqlalchemy`
- `psycopg2-binary`
- `pydantic-settings`
- `alembic`
- `pytest`
- `httpx`

---

## Virtual Environment Workflow

Activate the virtual environment every time you start backend development.

From the repository root:

```bash
source backend/venv/bin/activate
```

Or, if you are already inside `backend/`:

```bash
source venv/bin/activate
```

When active, your terminal prompt will be prefixed with `(venv)`.

To leave the virtual environment:

```bash
deactivate
```

---

## Current Backend Structure

```
backend/
├── .env.example
├── DATABASE_SETUP_README.md
├── README.md
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   │   └── config.py
│   ├── database/
│   │   ├── db.py
│   │   └── sports_prediction_schema.sql
│   ├── routes/
│   ├── schemas/
│   ├── models/
│   ├── services/
│   └── ml/
├── docs/
└── tests/
```

- **`app/main.py`** — creates the FastAPI application instance and defines the `/health` endpoint
- **`app/core/`** — application configuration; `config.py` loads database settings from environment variables via Pydantic Settings
- **`app/database/`** — SQLAlchemy engine/session setup (`db.py`) and the raw PostgreSQL schema (`sports_prediction_schema.sql`)
- **`app/routes/`** — placeholder for future FastAPI route modules (no routes defined yet)
- **`app/models/`** — placeholder for future SQLAlchemy ORM models (none defined yet)
- **`app/schemas/`** — placeholder for future Pydantic request/response schemas (none defined yet)
- **`app/services/`** — placeholder for future business logic / service layer code (none defined yet)
- **`app/ml/`** — existing data preparation and model training scripts (e.g. NFL data prep and a baseline training script) used for offline machine learning experimentation; not currently wired into the FastAPI app
- **`tests/`** — placeholder for future automated tests using pytest/httpx
- **`.env.example`** — committed template of required environment variables
- **`requirements.txt`** — pinned list of Python dependencies for the backend
- **`DATABASE_SETUP_README.md`** — full PostgreSQL and schema setup guide

---

## Troubleshooting

**PostgreSQL isn't running**

```bash
brew services start postgresql@17
pg_isready
```

**Python package/module not found**

Make sure your virtual environment is active, then reinstall dependencies:

```bash
pip install -r backend/requirements.txt
```

**`.env` doesn't exist**

```bash
cp backend/.env.example backend/.env
```

**Port 8000 already in use**

Another development server may already be running. Stop it, or start Uvicorn temporarily on a different port:

```bash
uvicorn app.main:app --reload --port 8001
```

**Database connection fails**

1. Verify PostgreSQL is running (`pg_isready`)
2. Verify the values in `backend/.env` are correct
3. Confirm the `sports_betting` database exists and the schema has been loaded
4. See `backend/DATABASE_SETUP_README.md` for full setup steps

---

## Quick Start

For a teammate who has already installed PostgreSQL and set up the `sports_betting` database:

```bash
python3 -m venv backend/venv
source backend/venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
# Edit backend/.env with your local PostgreSQL credentials
cd backend
uvicorn app.main:app --reload
```

Then visit:

```
http://127.0.0.1:8000/docs
```

and test:

```
GET /health
```
