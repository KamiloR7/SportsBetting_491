# Sports Data Ingestion and Refresh Guide

## Overview

This document describes how to run, validate, and refresh the Sprint 2 sports-data ingestion pipeline for the SportsBetting_491 project.

The Sprint 2 data pipeline supports team and match/game data for:

- Premier League
- NBA
- NFL

The pipeline is designed to normalize data from different sports sources into a consistent structure, validate the records, and prepare them for duplicate-safe storage in PostgreSQL.

The ingestion process is designed so that refreshing existing match data updates an existing match instead of creating a duplicate database record.

---

## 1. Pipeline Overview

The Sprint 2 data flow is:

```text
Sports Data Source
        |
        v
Collector
        |
        v
Normalization
        |
        v
Validation
        |
        v
PostgreSQL Match Upsert
        |
        v
Insert New Match
or
Update Existing Match
```

Automated pytest tests and GitHub Actions are used to validate the pipeline.

---

## 2. Supported Sports

### Premier League

Premier League data uses the football-data.org soccer collector with the Premier League competition code:

```text
PL
```

The collector normalizes team information, match dates, home and away teams, scores, statuses, and competition information.

### NBA

The NBA collector is located under:

```text
src/sportsbetting/collectors/nba.py
```

It collects and normalizes NBA team and game data and supports writing collected data to the project's raw-data directory.

### NFL

The NFL collector is located at:

```text
nfl_collector.py
```

It normalizes NFL team and game information into the shared sports-data format.

---

## 3. Python Environment

Create and activate a Python virtual environment before running the pipeline.

Example:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install pytest:

```bash
python -m pip install pytest
```

Install the backend dependencies:

```bash
python -m pip install -r backend/requirements.txt
```

The backend requirements include the packages needed for PostgreSQL and SQLAlchemy support.

---

## 4. PostgreSQL Setup

The project uses PostgreSQL for persistent storage.

Detailed database setup instructions are available in:

```text
backend/DATABASE_SETUP_README.md
```

The shared database schema is located at:

```text
backend/app/database/sports_prediction_schema.sql
```

The expected database name is:

```text
sports_betting
```

Database credentials are configured using environment variables.

See:

```text
backend/.env.example
```

Do not commit local database passwords or other credentials to GitHub.

---

## 5. Load the Database Schema

Follow the PostgreSQL setup guide before running database-dependent ingestion.

The schema creates the project tables, including:

- sports
- leagues
- seasons
- teams
- matches
- data_sources
- external_mappings
- ingestion_runs

The `external_mappings` table is used to associate an external source match identifier with the internal PostgreSQL match record.

This allows subsequent ingestion runs to locate and update an existing match.

---

## 6. Seed Reference Data

The project includes reference data for sports, leagues, and teams.

From the backend directory, run:

```bash
cd backend
python -m app.database.seed_data
```

The seed process is designed to avoid recreating existing reference records.

Return to the repository root afterward:

```bash
cd ..
```

---

## 7. Collect Sports Data

### Premier League

The existing soccer collector supports configurable football-data.org competition codes.

Premier League uses:

```text
PL
```

A `FOOTBALL_DATA_API_TOKEN` is required when making live requests to football-data.org.

The collector also supports injected data loaders, which are used by the automated tests so the test suite does not depend on a live external API.

### NBA

The NBA collector can be run through the Python package added to the project.

Example:

```bash
PYTHONPATH=src python -m sportsbetting.collectors.nba \
  --start-date YYYY-MM-DD \
  --end-date YYYY-MM-DD
```

Collected NBA data is written under the project's data directory according to the collector configuration.

### NFL

NFL collection is implemented in:

```text
nfl_collector.py
```

Refer to the collector's command-line options or module documentation for the available collection parameters.

---

## 8. Normalize Data

The shared multi-sport normalizer is located at:

```text
backend/src/normalizers/multi_sport_normalizer.py
```

The normalizer converts source-specific records into a common representation.

Normalized match information includes fields such as:

```text
game_id
sport
league
season
game_date
kickoff_utc
home_team_id
away_team_id
home_score
away_score
status
source
```

The normalizer also standardizes:

- sport values
- league information
- team identifiers
- team abbreviations
- home and away fields
- timestamps
- scores
- match status
- source information

---

## 9. Validate Match Records

Additional match validation is implemented in:

```text
data/validation.py
```

Validation checks include:

- required match identifier
- required sport
- required home team
- required away team
- home and away teams cannot be identical
- supported match statuses

Supported normalized statuses include:

```text
scheduled
in_progress
completed
postponed
cancelled
```

Invalid records should be rejected before they are stored.

---

## 10. PostgreSQL Match Upsert

Match database ingestion is implemented in:

```text
backend/app/database/match_ingestion.py
```

The ingestion process uses the normalized external game ID and source information to determine whether the match has already been stored.

### New Match

For a new external match:

```text
External Match
      |
      v
No Existing Mapping
      |
      v
INSERT into matches
      |
      v
Create external_mappings record
```

### Existing Match

When the same external match is ingested again:

```text
External Match
      |
      v
Existing external_mappings Record
      |
      v
Find Existing matches.id
      |
      v
UPDATE Existing Match
```

The existing match is updated instead of inserting a second match row.

Fields that may be refreshed include:

- start time
- match status
- home score
- away score
- updated timestamp

---

## 11. Status Mapping

The normalized pipeline and PostgreSQL schema use slightly different terminology for completed games.

During database ingestion:

```text
Normalized Status     PostgreSQL Status
----------------------------------------
scheduled             scheduled
in_progress           in_progress
completed             final
postponed             postponed
cancelled             cancelled
```

This conversion is handled by the match-ingestion layer.

---

## 12. Refreshing Match Data

Sports data should be refreshed by running the collector and ingestion process again.

A typical match may initially be collected as:

```text
status: scheduled
home_score: null
away_score: null
```

After the match is completed, a later refresh may produce:

```text
status: completed
home_score: 27
away_score: 20
```

The ingestion layer should find the existing match using its source and external match ID and update the existing database record.

The expected result is:

```text
First ingestion:
1 external match -> 1 PostgreSQL match

Second ingestion:
same external match -> same PostgreSQL match updated

Final row count:
1 match
```

It should not produce:

```text
First ingestion:
1 row

Second ingestion:
2 duplicate rows
```

---

## 13. Logging and Error Handling

The match-ingestion layer logs important ingestion operations.

Examples include:

- processing a match
- inserting a new match
- updating an existing match
- rejecting unsupported match statuses

The collectors also contain source-specific validation and error handling.

Errors should be reported clearly instead of silently inserting invalid records.

---

## 14. Run Automated Tests

From the repository root, run:

```bash
python -m pytest -v
```

The Sprint 2 test suite covers areas including:

- NFL collection and normalization
- soccer collection and normalization
- Premier League competition handling
- NBA collection and normalization
- shared multi-sport normalization
- duplicate detection
- missing-value validation
- match-status validation
- PostgreSQL match insert/update behavior
- invalid ingestion status handling

All tests should pass before a pull request is merged.

---

## 15. Continuous Integration

The project CI workflow is located at:

```text
.github/workflows/ci.yml
```

GitHub Actions automatically runs when:

- a pull request targets `main`
- changes are pushed or merged into `main`

The CI workflow installs the required Python/backend dependencies and executes the automated pytest suite.

A failed required test causes the CI workflow to fail.

---

## 16. Build Identification

CI builds use a unique build identifier based on the GitHub Actions run number and commit SHA.

Format:

```text
build-<run-number>-<short-commit-sha>
```

Example:

```text
build-14-8d514db
```

This makes each CI execution traceable to a specific source-code revision.

---

## 17. Troubleshooting

### pytest is not installed

Install it inside the active virtual environment:

```bash
python -m pip install pytest
```

### SQLAlchemy is missing

Install the backend requirements:

```bash
python -m pip install -r backend/requirements.txt
```

### PostgreSQL connection fails

Verify PostgreSQL is running and review:

```text
backend/DATABASE_SETUP_README.md
```

Also confirm that your local environment configuration matches:

```text
backend/.env.example
```

### football-data.org request fails

Verify that:

```text
FOOTBALL_DATA_API_TOKEN
```

is configured correctly.

Automated tests should use controlled test data rather than depending on the availability of an external API.

### Duplicate match appears

Verify that:

1. the source name is populated,
2. the external game ID is stable,
3. the match has an `external_mappings` entry,
4. subsequent ingestion uses the same source and external game ID.

---

## 18. Sprint 2 Verification Checklist

Before considering the Sprint 2 data pipeline complete:

- [ ] Premier League data can be normalized.
- [ ] NBA data can be collected and normalized.
- [ ] NFL data can be collected and normalized.
- [ ] Required match fields are validated.
- [ ] Match statuses are standardized.
- [ ] Duplicate normalized records are handled.
- [ ] New matches can be inserted into PostgreSQL.
- [ ] Existing matches can be updated without creating duplicates.
- [ ] Source information is preserved.
- [ ] Match updates refresh `updated_at`.
- [ ] Basic ingestion logging/error handling is present.
- [ ] The complete pytest suite passes.
- [ ] GitHub Actions passes on the pull request.
- [ ] A teammate reviews the pull request before merge.

---

## Sprint 2 Result

The completed Sprint 2 data-engineering pipeline provides a repeatable process for collecting, normalizing, validating, and storing team-match data for Premier League, NBA, and NFL.

The pipeline is designed so that sports data can be refreshed while existing matches are updated rather than duplicated. Automated tests and GitHub Actions provide repeatable validation of the pipeline before changes are merged.