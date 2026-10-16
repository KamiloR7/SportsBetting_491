# Historical match loading (DATA-25)

Call `app.database.historical_import.load_historical_matches(engine, records)`
with canonical dictionaries and an explicitly selected PostgreSQL engine.
This module never imports the application's configured engine and does not
collect data or choose a database. Maximum input batch size is 1000 records.

DATA-24 validation runs before opening a database transaction. Its accepted,
rejected and duplicate details are returned under `validation`. Completed
records need an actual timezone-aware kickoff and an existing season. Date-only
and nonfinal rows are deferred with reasons; no midnight times are fabricated.

Existing sports and leagues must resolve uniquely within their sport. Team
external mappings are preferred and their targets are checked against the sport;
otherwise exact name or abbreviation must identify exactly one team. Missing
mappings for ID-only records must be prepared explicitly. Seasons use NFL/MLB
year labels, e.g. `2024`, and EPL `2024-25`, scoped to the league. No sport,
league, team, season or team mapping is automatically created. Source records
are created only during eligible match writes.

A single transaction-scoped advisory lock (491025) serializes cooperating
historical importers. All references are preflighted before match writes.
Reference failures defer individual records; SQL, identity, write and commit
failures roll back the entire batch. `matches_inserted`/`matches_updated` count
committed writes only, including zero after rollback. Updates preserve match ID,
reject league/team/established-season changes, allow corrected scores/kickoffs,
and retain existing neutral-site/season values when omitted. A repeated identical
import counts as an update. There is no uniqueness assumption based on date and
teams, so distinct MLB doubleheaders remain distinct.

The low-level `upsert_match` retains its match-ID return value, requires an active
transaction, and does not perform DATA-24 validation or take the importer lock.
Use the batch loader for historical ingestion. Direct unrelated writers do not
participate in the concurrency guarantee. Cross-provider reconciliation is not
automatic. Demo rows are not adopted by name/date matching: only external match
mappings select rows for update. Prefer separate databases for demo and historical
data; mapped-source filtering is needed if both coexist. No schema changes occur.

Summary fields include records read/accepted/rejected, identical duplicates,
deferred records with reasons, committed insert/update counts, transaction failure
details, and a committed flag (false when no transaction was needed). A caller
must check failure details; the loader returns failures rather than raising SQL
exceptions. Batch-size errors raise before any transaction. Logging should avoid
publishing connection credentials or raw database exception details externally.

## Tests

Unit tests use fake connections and a rollback-capable fake engine. PostgreSQL
integration tests are opt-in. Provision a disposable local database named exactly
`sportsbetting_data25_test`, set `DATA25_DISPOSABLE_POSTGRES_URL` to its SQLAlchemy
PostgreSQL URL and `DATA25_ALLOW_DISPOSABLE_TEST=1`, then run
`python -m pytest backend/tests/test_historical_import_postgres.py` with
`PYTHONPATH=backend:src`. Each test creates/drops a random schema; never configure
these variables for a shared, production or demo database. Without explicit
configuration, tests skip and make no connection.

The DATA-26 CLI below provides file input, explicit database selection, dry-run
validation, application logging, exit codes, and batch orchestration. Full-season
reference coverage, date-only enrichment, source/team aliases and persistent
database run logging remain handoff work.

## Repeatable command (DATA-26)

From the repository root, use Python 3.12 with backend dependencies installed
(`python -m pip install -r backend/requirements.txt`). The import CLI uses no
application database defaults and performs no sports downloads.

```bash
PYTHONPATH=backend:src python -m app.database.import_historical \
  --input data/development/nfl_games_2024.csv --sport NFL --format csv --dry-run

PYTHONPATH=backend:src python -m app.database.import_historical \
  --input data/raw/mlb_source_0.bin --sport MLB --format mlb-schedule --dry-run

PYTHONPATH=backend:src python -m app.database.import_historical \
  --input data/local/E0.csv --sport EPL --format epl-csv --season 2023-24 --dry-run
```

Paths above are examples; explicitly select files already present locally.

Formats:

- `json`: JSON list of canonical/collector-normalized records with league/source.
- `csv`: canonical CSV, including NFL or football-data.org PL collector output.
- `mlb-schedule`: already-downloaded Stats API `dates[].games[]` JSON.
- `mlb-csv`: existing six-column ML export; use `--season 2024` if needed.
- `epl-csv`: football-data.co.uk E0 rows; provide `--season` or a `Season` column.

`--input` accepts multiple files for one sport and format. All inputs are validated
and deduplicated together before splitting writes with `--batch-size` (1–1000,
default 1000), so duplicates/conflicts spanning files or batches are detected.
Files are currently held in memory; select bounded local datasets.

Dry runs do not create an engine, connect, resolve database references, or write
PostgreSQL. They report validation and known date/status deferrals. A clean dry
run does not establish that team/season mappings exist in the target database.

For live use, provision a separate **local import-only** PostgreSQL database
named `sportsbetting_import_*`. Set `HISTORICAL_IMPORT_DATABASE_URL` securely to
its SQLAlchemy PostgreSQL URL; do not put credentials in command arguments.
Then explicitly select the same database and opt in to writes:

```bash
PYTHONPATH=backend:src python -m app.database.import_historical \
  --input data/local/normalized_matches.json --sport NFL --format json \
  --database-name sportsbetting_import_sprint3 --allow-write
```

Only localhost/loopback URLs are accepted. Database names must match the explicit
selection, use the import prefix, and exclude prod/shared/demo markers. URL query
overrides are refused. Never point this configuration at shared or demo data.
`--database-url-env NAME` selects an alternative environment-variable name.
Prepare the schema and required sport/team/season references separately first.

A JSON report goes to stdout; timestamped standard logging goes to stderr. Logs
include selected files, sport/sources, counts, record rejection/defer reasons,
and batch failure/rollback events. Database exception messages and URLs are not
printed. Redirect stderr to an approved log file for persistence if desired.
The CLI does not write `ingestion_runs`: durable failure logging needs a separate
transaction policy, especially when the import transaction rolls back. No schema
changes were introduced for logging.

Example summary fields (the actual output also contains detail arrays):

```json
{"records_read": 4, "records_accepted": 2, "records_rejected": 1,
 "duplicates_collapsed": 1, "records_deferred": 1,
 "matches_inserted": 0, "matches_updated": 0, "dry_run": true}
```

Exit codes: **0** success, **1** rejected/deferred records, **2** input/configuration
error, **3** database batch failure. Valid records may be imported even when other
records are rejected/deferred; inspect counts. Each batch is atomic, not the
entire multi-batch invocation. Earlier committed batches remain committed after
a later failure; subsequent batches stop and unattempted records are reported.
Repeated execution updates source-mapped matches rather than duplicating them.

Reduced MLB CSVs lack kickoff times and display metadata; EPL result CSVs may
lack kickoff times, provider IDs and abbreviations. These records can pass data
validation but remain deferred until genuine times and reference mappings are
available. Suspended/incomplete/nonfinal records are deferred. The CLI does not
invent times, populate unknown teams, reconcile cross-provider identities, or
change existing ML outcome semantics.
