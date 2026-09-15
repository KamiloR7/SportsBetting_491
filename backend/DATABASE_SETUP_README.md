# Sports Betting Database Setup

This guide explains how to set up the local PostgreSQL database used by the CPSC 491 Sports Match-Prediction Application.

The project database schema is defined in:

```text
database/sports_prediction_schema.sql
```

The schema is designed for PostgreSQL and supports the project's FastAPI + PostgreSQL + SQLAlchemy + Alembic backend plan.

---

## 1. Install PostgreSQL

### macOS with Homebrew

If Homebrew is already installed, install PostgreSQL 17:

```bash
brew install postgresql@17
```

Start PostgreSQL:

```bash
brew services start postgresql@17
```

Confirm that PostgreSQL is running:

```bash
pg_isready
```

You should see a message indicating that PostgreSQL is accepting connections.

You can also confirm the installed version:

```bash
psql --version
```

---

## 2. Install pgAdmin 4

Download and install pgAdmin 4 if you want a graphical interface for PostgreSQL.

Official site:

```text
https://www.pgadmin.org/download/
```

pgAdmin is optional. The database can also be created and managed entirely from the Terminal.

---

## 3. Confirm Your PostgreSQL User

Homebrew normally creates a PostgreSQL role that matches your macOS username.

Check your macOS username:

```bash
whoami
```

Then connect to PostgreSQL:

```bash
psql postgres
```

Once connected, list PostgreSQL roles:

```sql
\du
```

If a `postgres` superuser role does not exist and the team wants to use the same setup instructions, exit PostgreSQL:

```sql
\q
```

Then create the `postgres` superuser:

```bash
createuser -s postgres
```

Test it:

```bash
psql -U postgres -d postgres
```

Inside PostgreSQL, run:

```sql
\du
```

The `postgres` role should show `Superuser`.

> Each teammate has their own local PostgreSQL installation. Do not share PostgreSQL passwords or commit credentials to GitHub.

---

## 4. Register the Local Server in pgAdmin

Open pgAdmin 4.

Right-click:

```text
Servers -> Register -> Server
```

### General tab

Use any descriptive name, for example:

```text
Sports_Betting
```

### Connection tab

Use:

```text
Host name/address: localhost
Port: 5432
Maintenance database: postgres
Username: postgres
```

Enter your local PostgreSQL password only if one has been configured.

Save the server connection.

> `Sports_Betting` is only the pgAdmin server connection name. It is not the project database name.

---

## 5. Create the Project Database

In pgAdmin, expand your server and right-click:

```text
Databases -> Create -> Database
```

Use:

```text
Database: sports_betting
Owner: postgres
```

Click **Save**.

After creation, pgAdmin should show:

```text
Databases
├── postgres
└── sports_betting
```

Do not delete the default `postgres` database.

### Terminal alternative

The same database can be created with:

```bash
createdb -U postgres sports_betting
```

---

## 6. Load the Project Schema in pgAdmin

In pgAdmin:

1. Right-click the `sports_betting` database.
2. Select **Query Tool**.
3. Click the **Open File** button.
4. Open:

```text
database/sports_prediction_schema.sql
```

5. Confirm the Query Tool is connected to the `sports_betting` database.
6. Click **Execute** or press `F5`.

The Messages panel should end with something similar to:

```text
COMMIT
Query returned successfully
```

---

## 7. Confirm the Tables Were Created

In pgAdmin, expand:

```text
sports_betting
└── Schemas
    └── public
        └── Tables
```

Right-click **Tables** and select **Refresh**.

The database should contain 13 tables:

```text
data_sources
external_mappings
ingestion_runs
leagues
match_predictions
matches
model_versions
season_teams
seasons
sports
teams
user_predictions
users
```

You can also verify them from the Query Tool:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

---

## 8. Terminal Alternative for Loading the Schema

Instead of pgAdmin, the schema can be loaded directly from the repository root:

```bash
psql -U postgres -d sports_betting -f database/sports_prediction_schema.sql
```

Then connect to the database:

```bash
psql -U postgres -d sports_betting
```

List the tables:

```sql
\dt
```

Confirm the current database connection:

```sql
\conninfo
```

Exit PostgreSQL:

```sql
\q
```

---

## 9. Important Team Rules

- Keep `sports_prediction_schema.sql` in GitHub as the shared database schema.
- Do not create or change project tables only through the pgAdmin GUI without also updating the schema or a future migration.
- Do not commit database passwords, local credentials, or environment secrets.
- Each developer runs their own local PostgreSQL server and local `sports_betting` database.
- The SQL schema in the repository is the shared source of truth for the database structure.
- Later database changes should be managed through SQLAlchemy models and Alembic migrations once the backend implementation reaches that stage.

---

## 10. Troubleshooting

### `role "postgres" does not exist`

Homebrew may have created only a PostgreSQL role matching your macOS username.

Create the standard local superuser:

```bash
createuser -s postgres
```

Then test:

```bash
psql -U postgres -d postgres
```

### `connection refused`

Check whether PostgreSQL is running:

```bash
brew services list
```

Start it if necessary:

```bash
brew services start postgresql@17
```

Then verify:

```bash
pg_isready
```

### pgAdmin is slow

pgAdmin is only a graphical interface. PostgreSQL can be managed directly from Terminal with `psql`, `createdb`, and other PostgreSQL command-line tools.

### Tables do not appear after running the schema

In pgAdmin:

```text
Schemas -> public -> Tables -> Right-click -> Refresh
```

Also make sure the Query Tool was connected to `sports_betting`, not the default `postgres` database.

---

## Quick Setup Summary

For teammates using Homebrew:

```bash
brew install postgresql@17
brew services start postgresql@17
createuser -s postgres
createdb -U postgres sports_betting
psql -U postgres -d sports_betting -f database/sports_prediction_schema.sql
```

Then verify:

```bash
psql -U postgres -d sports_betting
```

```sql
\dt
```

If all 13 project tables are listed, the local database setup is complete.
