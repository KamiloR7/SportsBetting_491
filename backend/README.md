# Sports Match Prediction — Backend

This directory contains the FastAPI backend for the CPSC 491 Sports Match Prediction application.

The Sprint 1 backend currently includes:

* FastAPI application setup
* Environment-based PostgreSQL configuration
* SQLAlchemy database connection/session management
* PostgreSQL schema for the multi-sport application
* Initial seed data for sports, leagues, and teams
* Read-only API endpoints for sports, leagues, and teams
* FastAPI Swagger/OpenAPI documentation
* Health-check endpoint

Prediction functionality, authentication, write endpoints, and production deployment are planned for future sprints.

---

## Technology Stack

* **FastAPI** — web framework used to build the API
* **PostgreSQL** — relational database for storing sports, teams, matches, and predictions
* **SQLAlchemy** — Python SQL toolkit used to communicate with PostgreSQL
* **Pydantic Settings** — loads and validates configuration from environment variables
* **Uvicorn** — ASGI server used to run the FastAPI application locally
* **Alembic** — available for future database migration support
* **pytest / httpx** — available for future automated backend testing

---

## Machine-Level Prerequisites

Install these directly on your computer. They are not installed by `pip`.

* Git
* Python 3
* Homebrew (for the macOS PostgreSQL setup below)
* PostgreSQL 17
* pgAdmin 4 — optional, but recommended for browsing and querying the database

Python packages such as FastAPI and SQLAlchemy are declared in `backend/requirements.txt` and should be installed together.

---

## PostgreSQL Prerequisite

On macOS with Homebrew:

```bash
brew install postgresql@17
brew services start postgresql@17
pg_isready
```

`pg_isready` should report that PostgreSQL is accepting connections.

This backend requires a local database named:

```text
sports_betting
```

The database must have the project schema loaded before database-dependent API routes will work.

Full PostgreSQL and pgAdmin setup instructions are available in:

```text
backend/DATABASE_SETUP_README.md
```

The schema is located at:

```text
backend/app/database/sports_prediction_schema.sql
```

---

## First-Time Backend Setup

Run the following commands from the repository root:

```bash
python3 -m venv backend/venv
source backend/venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
```

What each command does:

1. `python3 -m venv backend/venv` — creates an isolated Python environment
2. `source backend/venv/bin/activate` — activates the virtual environment
3. `pip install -r backend/requirements.txt` — installs the backend dependencies
4. `cp backend/.env.example backend/.env` — creates your local environment configuration file

After creating `.env`, update it with your own PostgreSQL credentials.

---

## Environment Variables

Edit `backend/.env`:

```env
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=sports_betting
DATABASE_USER=postgres
DATABASE_PASSWORD=your_local_password
```

Important:

* `.env.example` contains placeholder values and is safe to commit.
* `backend/.env` contains local credentials and must not be committed.
* `.env` is excluded through `.gitignore`.
* Database credentials must never be hard-coded into Python files.
* Each teammate may have different PostgreSQL credentials.

Configuration is loaded through:

```text
backend/app/core/config.py
```

---

## Load the Database Schema

Before running the database-dependent endpoints, create the `sports_betting` database and load:

```text
backend/app/database/sports_prediction_schema.sql
```

See:

```text
backend/DATABASE_SETUP_README.md
```

for the complete pgAdmin/PostgreSQL setup procedure.

---

## Seed Initial Data

After the schema has been loaded and `.env` is configured, populate the initial reference data.

From `backend/`:

```bash
python -m app.database.seed_data
```

Expected output:

```text
Seed data applied (sports, leagues, teams).
```

The seed script currently inserts initial reference data for:

* Basketball — NBA
* American Football — NFL
* Baseball — MLB
* Hockey — NHL
* Soccer — English Premier League (EPL)

It also inserts a small Sprint 1 development set of teams for each sport.

The seed script is designed to avoid creating duplicate records when run more than once.

Seed implementation:

```text
backend/app/database/seed_data.py
```

---

## Running FastAPI

From the repository root:

```bash
cd backend
uvicorn app.main:app --reload
```

Or, if already inside `backend/`:

```bash
uvicorn app.main:app --reload
```

A successful startup should include:

```text
Uvicorn running on http://127.0.0.1:8000
Application startup complete.
```

Press `Ctrl+C` to stop the server.

---

## Development URLs

While FastAPI is running:

```text
Swagger Docs: http://127.0.0.1:8000/docs
OpenAPI JSON: http://127.0.0.1:8000/openapi.json
Health Check: http://127.0.0.1:8000/health
Sports:       http://127.0.0.1:8000/sports
Leagues:      http://127.0.0.1:8000/leagues
Teams:        http://127.0.0.1:8000/teams
```

There is currently no route defined for:

```text
http://127.0.0.1:8000/
```

so visiting the root URL will return `404 Not Found`. This is expected.

FastAPI automatically generates the interactive Swagger interface at `/docs`.

---

## API Endpoints

### Health Check

```http
GET /health
```

Expected response:

```json
{
  "status": "ok"
}
```

This endpoint confirms that the FastAPI application is running. It does not currently perform a PostgreSQL health check.

### Sports

```http
GET /sports
```

Returns the sports currently stored in PostgreSQL.

Example response structure:

```json
[
  {
    "id": 1,
    "name": "Basketball",
    "slug": "basketball"
  }
]
```

### Leagues

```http
GET /leagues
```

Returns leagues and their associated sport information.

Example response structure:

```json
[
  {
    "id": 1,
    "name": "National Basketball Association",
    "abbreviation": "NBA",
    "country": "USA",
    "active": true,
    "sport": {
      "id": 1,
      "name": "Basketball",
      "slug": "basketball"
    }
  }
]
```

### Teams

```http
GET /teams
```

Returns teams and their associated sport information.

Example response structure:

```json
[
  {
    "id": 1,
    "name": "Los Angeles Lakers",
    "abbreviation": "LAL",
    "city": "Los Angeles",
    "active": true,
    "sport": {
      "id": 1,
      "name": "Basketball",
      "slug": "basketball"
    }
  }
]
```

The current database schema associates teams directly with sports through `teams.sport_id`.

---

## Python Dependencies

Install all backend dependencies with:

```bash
pip install -r backend/requirements.txt
```

Current dependencies include:

* `fastapi`
* `uvicorn[standard]`
* `sqlalchemy`
* `psycopg2-binary`
* `pydantic-settings`
* `alembic`
* `pytest`
* `httpx`

---

## Virtual Environment Workflow

Activate the virtual environment whenever working on the backend.

From the repository root:

```bash
source backend/venv/bin/activate
```

From inside `backend/`:

```bash
source venv/bin/activate
```

When active, the terminal prompt should begin with:

```text
(venv)
```

To deactivate:

```bash
deactivate
```

---

## Current Backend Structure

```text
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
│   │   ├── seed_data.py
│   │   └── sports_prediction_schema.sql
│   ├── routes/
│   │   └── sports.py
│   ├── schemas/
│   │   └── sports.py
│   ├── models/
│   ├── services/
│   └── ml/
├── docs/
└── tests/
```

### Important Files

* **`app/main.py`** — creates the FastAPI application, registers API routers, and defines `/health`
* **`app/core/config.py`** — loads environment-based database configuration
* **`app/database/db.py`** — creates the SQLAlchemy engine and database session dependency
* **`app/database/sports_prediction_schema.sql`** — PostgreSQL database schema
* **`app/database/seed_data.py`** — inserts initial sports, leagues, and teams
* **`app/routes/sports.py`** — implements the `/sports`, `/leagues`, and `/teams` routes
* **`app/schemas/sports.py`** — Pydantic response schemas for the reference-data endpoints
* **`app/models/`** — reserved for future ORM models
* **`app/services/`** — reserved for future business/service logic
* **`app/ml/`** — offline machine-learning experimentation code; not currently connected to FastAPI
* **`tests/`** — reserved for automated backend tests
* **`.env.example`** — committed environment-variable template
* **`requirements.txt`** — Python backend dependencies
* **`DATABASE_SETUP_README.md`** — PostgreSQL and schema setup instructions

---

## Verifying the Backend

After configuring the database, loading the schema, and running the seed script:

```bash
uvicorn app.main:app --reload
```

Then verify:

```text
GET /health
GET /sports
GET /leagues
GET /teams
```

All four routes should return HTTP:

```text
200 OK
```

The easiest way to test them manually is through:

```text
http://127.0.0.1:8000/docs
```

---

## Troubleshooting

### PostgreSQL isn't running

```bash
brew services start postgresql@17
pg_isready
```

### Python package/module not found

Make sure the virtual environment is active.

From the repository root:

```bash
source backend/venv/bin/activate
pip install -r backend/requirements.txt
```

### `.env` doesn't exist

From the repository root:

```bash
cp backend/.env.example backend/.env
```

Then edit the new file with your PostgreSQL credentials.

### Port 8000 already in use

Stop the other process or temporarily use another port:

```bash
uvicorn app.main:app --reload --port 8001
```

### Database connection fails

1. Verify PostgreSQL is running with `pg_isready`
2. Check the values in `backend/.env`
3. Confirm the `sports_betting` database exists
4. Confirm the schema has been loaded
5. See `backend/DATABASE_SETUP_README.md`

### API routes return database errors

Confirm that:

1. PostgreSQL is running
2. `.env` contains the correct credentials
3. The schema has been loaded
4. The seed script has been run:

```bash
python -m app.database.seed_data
```

---

## Quick Start

For a teammate who already has PostgreSQL 17 installed:

```bash
python3 -m venv backend/venv
source backend/venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
```

Edit:

```text
backend/.env
```

with your local PostgreSQL credentials.

Create the `sports_betting` database and load:

```text
backend/app/database/sports_prediction_schema.sql
```

Then:

```bash
cd backend
python -m app.database.seed_data
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

Verify:

```text
GET /health
GET /sports
GET /leagues
GET /teams
```

All endpoints should return `200 OK` when the backend and database are configured correctly.