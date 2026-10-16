# SCRUM-203 — Data quality and sample refresh QA

**Result: partially satisfied.** All executed offline tests pass. Actual
PostgreSQL persistence/rollback and historical dataset quality remain unverified.
This report supersedes the earlier 273-pass assessment for a different checkout.

## Verified workspace and environment

- QA date: 2026-10-15, America/Los_Angeles.
- Working directory: `/private/tmp/SportsBetting_491-official-normalization`.
- Branch: `member3/sprint3-data-qa`.
- HEAD: `527f2b873906e7b1183fc354d8a76f40d133f105`, merge PR #31.
- Working tree was clean before QA. The historical loader, CLI, DATA-24
  validator, and all requested ingestion test modules are present here.
- macOS 26.3.1 arm64; Python 3.12.5; pytest 9.1.1; pandas 3.0.6;
  SQLAlchemy 2.0.54; psycopg2 2.9.13.
- Interpreter reused from the existing environment at
  `/Users/meelohh/Documents/cpsc491_sportsbetting/SportsBetting_491/backend/venv/bin/python`.
  Tests and application modules were loaded from the verified worktree via
  `PYTHONPATH`; no packages were installed.

Before any changes, executed `pwd`, `git branch --show-current`,
`git rev-parse HEAD`, `git status --short`, `git cat-file -t 527f2b8`,
and file existence checks. All workspace requirements matched.

Reviewed `docs/sprint3-data-validation-checklist.md`, the DATA-24 validator and
tests, historical importer and CLI and their tests, match ingestion and sport
normalizers, `backend/docs/historical_match_import.md`, database setup/configuration,
and available data/fixture files. The checklist still says planning-only and
names NBA/NFL/UEFA; its criteria are assessed below for official NFL/MLB/EPL.
The original checklist was left unchanged.

## Commands and results

Commands ran from the verified worktree. `QA_PY` below abbreviates the absolute
interpreter path above. The focused run is a subset of regression; do not add
their totals.

```bash
QA_PY=/Users/meelohh/Documents/cpsc491_sportsbetting/SportsBetting_491/backend/venv/bin/python

PYTHONPATH=/tmp:.:backend:src "$QA_PY" -m pytest -p scrum203_offline_guard \
  tests/test_nfl_normalization.py tests/test_mlb_normalization.py \
  tests/test_epl_normalization.py tests/test_historical_match_validation.py \
  backend/tests/test_historical_import.py backend/tests/test_import_historical_cli.py \
  backend/tests/test_match_ingestion.py backend/tests/test_historical_import_postgres.py \
  -q -ra --junitxml=/tmp/scrum203-official-focused.xml

PYTHONPATH=/tmp:.:backend:src "$QA_PY" -m pytest -p scrum203_offline_guard \
  -q -ra --junitxml=/tmp/scrum203-official-regression.xml
```

The temporary plugin was preserved as [offline_guard.py](qa/scrum203/offline_guard.py).
It raises on Python socket connections/DNS and `psycopg2.connect`. To reproduce,
replace `/tmp` in `PYTHONPATH` with `backend/docs/qa/scrum203` and replace
`-p scrum203_offline_guard` with `-p offline_guard`. It does not block in-memory
SQLite used by unrelated regression tests. No live collectors were run;
collector tests use injected fixtures.

| Run | Passed | Failed | Skipped | Duration |
| --- | ---: | ---: | ---: | ---: |
| Focused data QA | 255 | 0 | 4 | 0.98 s |
| Full regression | 488 | 0 | 4 | 4.49 s |

JUnit evidence: [focused](qa/scrum203/focused.xml),
[regression](qa/scrum203/regression.xml). Both commands exited 0.
Full regression emitted five deprecation warnings concerning Starlette/httpx,
AnyIO BlockingPortal, and SQLite's default datetime adapter; no test failures.

| Focused module | Passed | Skipped |
| --- | ---: | ---: |
| NFL normalization | 36 | 0 |
| MLB normalization | 38 | 0 |
| EPL normalization | 49 | 0 |
| DATA-24 historical validation | 44 | 0 |
| DATA-25 historical import with fake engine | 29 | 0 |
| DATA-26 import CLI | 55 | 0 |
| Low-level match ingestion with fake connection | 4 | 0 |
| Real PostgreSQL integration | 0 | 4 |

## Checklist and acceptance evidence

| Criterion | Verified evidence and boundary |
| --- | --- |
| Nonempty source/match IDs and required fields | DATA-24 `test_rejections_with_explicit_reasons` rejects absent/blank/invalid IDs, excessive database field lengths, missing source/team identities, invalid sport/league, and malformed records. Rejections retain reasons and input indexes. |
| Distinct and known team references | Normalization rejects identical teams. Mock importer defers missing/ambiguous sport, league, team, and season references, dangling team mappings, and teams resolving to one internal ID. Provider team mappings resolve ID-only MLB records. Actual database reference coverage is pending. |
| ISO dates and aware timestamps | Sport suites and DATA-24 test invalid calendar dates, naive/bad timestamps, UTC conversion, DST, and CSV round trips. Date-only data is valid but deferred from historical writes; no kickoff is invented. |
| Scheduled versus completed scores | Scheduled missing scores pass validation; completed missing/negative/fractional/nonfinite or inconsistent scores are rejected. Nonfinal/suspended/incomplete records are deferred by historical import. |
| Identical duplicates collapse | DATA-24 `test_duplicate_report` observes read=4, accepted=2, rejected=1, duplicates=1. Normalized equivalent values also collapse. |
| Conflicting duplicates rejected | Every occurrence in a conflicting source/match group is rejected, in either input order. CLI tests reject conflicts across files before batching. |
| Source-scoped duplicate keys | DATA-24 `test_source_scoping_and_database_key`: same game ID with different sources remains distinct; same source/game ID across different leagues conflicts. The historical key is `(source, game_id)`, matching external match mappings. No cross-provider reconciliation is claimed. |
| Sport outcomes | NFL ties and EPL draws accepted in normalizer, DATA-24, loader, and CLI test cases. Completed MLB ties rejected. Caller-supplied NFL outcome conflicts are rejected for JSON/CSV in dry-run and mocked write modes. |
| Supported input files | CLI tests cover canonical JSON/CSV, MLB schedule JSON, reduced MLB CSV, EPL E0 CSV, malformed/absent inputs, format context, and date-only deferrals. These are synthetic local files. |
| Import summaries | Tests assert read/accepted/rejected/duplicate/deferred counts, committed insert/update counts, zero writes after rollback/commit failure, and unattempted records after batch failure. Accepted counts describe validation acceptance; deferred records are a subset and are not additional input rows. |

## CLI dry runs and mocked refresh

`test_dry_run_no_engine_or_loader` replaces both engine creation and loader calls
with functions that raise if invoked. It passes with read=2, accepted=1,
duplicates=1, inserted=0, exit code 0, and expected start/completion/source logs.
All three sports pass dry-run normalization. Negative scores and date-only input
produce explicit rejection/defer counts. A clean dry run does not verify database
references. Unsafe/missing database configurations are rejected in CLI tests.

The rollback-capable fake engine verifies:

- First import of two identical records inserts one, collapsing one duplicate.
  Corrected score/kickoff reimport updates the same stored mock match, retains
  one match/mapping, season ID 7 and neutral-site information, and takes the
  transaction advisory lock on both imports.
- Mock CLI import of two unique records in batches of one inserts two; repeating
  it reports two updates. Distinct MLB doubleheader IDs insert separately.
- Match/mapping write failures, later-record failure, and commit failure restore
  mock state and report zero committed batch writes. Identity/season changes and
  dangling match mappings produce transaction failures.
- A missing reference defers that record while allowing other eligible records.
  Provider mappings are preferred; omitted neutral-site values preserve prior
  values. Low-level writes require an active transaction.
- On a later CLI batch failure, earlier committed batches remain, later batches
  stop, unattempted rows are reported, and driver error details are sanitized.

These tests establish fake-engine behavior and SQL expectations, not actual
PostgreSQL transactions, constraints, concurrency, or persisted row counts.

## Real PostgreSQL status

**Four tests skipped; no authorized disposable database identified.** The invoking
process had no DATA25, PostgreSQL, database, or historical-import configuration
variables. No database connection was attempted. Application database settings
and ordinary local/shared/demo databases were not used as substitutes.

All four skips report: `No explicitly authorized disposable PostgreSQL test database`.
Pending integration tests are:

1. `test_postgres_reimport_correction_and_doubleheader`: first/second import,
   persistent IDs, score correction, season/neutral-site values, external mappings.
2. `test_postgres_forced_failure_rolls_back_batch`: trigger-induced failure and
   rollback of matches, mappings, and newly created sources.
3. `test_postgres_concurrent_imports_serialize`: concurrent imports yield one
   insert and one update, with one stored match.
4. `test_postgres_dangling_mapping_and_missing_reference`: dangling match mapping
   failure and missing season deferral.

Execution requires an explicitly authorized local disposable database named
`sportsbetting_data25_test`, its URL supplied securely through
`DATA25_DISPOSABLE_POSTGRES_URL`, and `DATA25_ALLOW_DISPOSABLE_TEST=1`.
Tests create and drop random schemas. Full persisted field/reference readback
should also be reviewed before claiming comprehensive record-retention coverage.

## Available dataset quality

Inventory command: `rg --files --hidden --no-ignore data`. Raw, sample, and
processed directories each contain only `.gitkeep`; no historical files are
available. A repository-wide CSV/Parquet/JSONL/NDJSON/XLSX inventory outside
dependency directories found only a manual-test evidence workbook, not a sports
historical dataset. No downloads were performed.

| Historical sport | Expected file | Actual rows | Missing fields | Duplicate IDs | Seasons / scores / source and team consistency |
| --- | --- | --- | --- | --- | --- |
| NFL | `data/raw/nfl_games.csv` absent | Unverified | Unverified | Unverified | Unverified |
| MLB | `data/raw/mlb_games.csv` absent | Unverified | Unverified | Unverified | Unverified |
| EPL | `data/raw/epl_games.csv` absent | Unverified | Unverified | Unverified | Unverified |

Absent files do not establish zero historical records or zero imported records.
Earlier Sprint 2 provenance documents are prior evidence, not current dataset
measurements; no counts were carried forward as newly verified statistics.

The committed `backend/tests/fixtures/sprint3_match_outcomes.json` was parsed
with Python `json` and counted by `sport` and `match_id` using `Counter`:

| Synthetic sport | Rows | Duplicate IDs (extra occurrences) | Missing/null home scores | Missing/null away scores | Final rows missing either score |
| --- | ---: | ---: | ---: | ---: | ---: |
| NFL | 3 | 0 | 0 | 0 | 0 |
| MLB | 3 | 0 | 1 | 1 | 0 |
| EPL | 4 | 0 | 0 | 1 | 1 |

All ten fixture records have IDs, dates, sport, and status. All lack source,
season, and home/away team IDs; no season coverage or source/team consistency can
be established. Missing MLB scores belong to its scheduled fixture. Missing EPL
away score is an intentional rejection fixture. These are outcome-label test
inputs, not ingestion-ready historical matches. The ten fixture tests pass.
Machine-readable measurements: [dataset-quality.json](qa/scrum203/dataset-quality.json).

## Remaining limitations and disposition

- Real PostgreSQL insert/reimport/correction, rollback, concurrency, and persisted
  reference/field retention remain unverified until the disposable target is authorized.
- Historical row counts, required-field completeness, duplicates, seasons, final
  scores, and identity/source quality require actual local historical files.
- Reduced MLB/EPL CSVs may lack genuine kickoff times or mapping metadata.
  Validation acceptance does not make them database-ready. Reference coverage,
  aliases, and date-only enrichment are documented handoff work.
- The importer serializes cooperating importers only; unrelated writers do not
  participate. Each batch is atomic, rather than the whole CLI invocation.
  Files are read into memory, and durable `ingestion_runs` logging is not implemented.
- The checklist's older sports/status wording needs a separate documentation
  alignment; its items were not globally marked complete from fixture evidence.

No new ingestion defect was demonstrated by this QA run. **Offline and mocked
acceptance is verified; overall SCRUM-203 is partially satisfied and should remain
open for database and historical-data evidence.** Only QA documentation/evidence
was added; ingestion implementation, ML algorithms, and frontend were unchanged.
No commits, pushes, or pull requests were made.
