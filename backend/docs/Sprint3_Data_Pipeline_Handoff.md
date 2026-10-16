# Sprint 3 data pipeline and ML handoff (DOC-20)

Scope: **NFL, MLB, EPL**. Reviewed on branch `member3/sprint3-data-qa` at
`83ac610` (QA evidence), with implementation base `527f2b8` (PR #31).
This is the operational handoff for DATA-20 through DATA-26; it does not claim
that historical data has been loaded into a database.

## 1. Architecture and evidence boundaries

```text
Provider retrieval (separate, explicitly initiated)
    -> local provider files / collector records
    -> sport normalizers -> canonical MATCH_FIELDS
    -> DATA-24 quality gate: accepted / rejected / identical duplicates
    -> DATA-25 eligibility and reference resolution
    -> one PostgreSQL transaction per batch: matches + source/match mappings
    -> repeat import updates mapped matches

ML consumption paths:
    local six-column CSV -> validation -> historical features -> training/inference
    database matches + leagues + teams -> existing training/API consumers
```

The CLI composes normalization, validation, and batch loading; collectors do not
automatically feed PostgreSQL. Database consumers exist, but there is no single
command that collects, imports, trains the Sprint 3 sport-aware model, and deploys it.

[SCRUM-203 QA](SCRUM-203-QA.md) records **488 passed, 0 failed, 4 PostgreSQL
tests skipped**; its focused data QA subset is 255 passed and 4 skipped.
Normalization, validation, CLI dry runs, summary counts, reference handling,
refresh, and rollback were exercised offline with synthetic inputs/fake engines.
Actual PostgreSQL persistence, concurrency, rollback, and real historical dataset
quality remain unverified. Those results were not rerun for this documentation change.

## 2. Sources and collection code that exists

| Sport | Existing retrieval implementation | Source and output behavior |
| --- | --- | --- |
| NFL | [nfl_collector.py](../../nfl_collector.py), `NFLCollector` | nflverse through optional `nflreadpy`; teams and schedules. CLI takes `--season`, `--output-dir`; default `data/development`, files `nfl_teams.csv`, `nfl_games_<season>.csv`. |
| EPL | [uefa_collector.py](../../uefa_collector.py), `UEFACollector` | football-data.org v4; explicitly choose `--competition-code PL` (default is CL, outside this handoff). Requires `FOOTBALL_DATA_API_TOKEN` for live requests. Default outputs `data/development/uefa_pl_teams.csv` and `uefa_pl_games_<season>.csv`. |
| NFL, MLB, EPL | [download_multisport_data.py](../app/ml/features/download_multisport_data.py) | Separate historical ML downloader: nflverse GitHub games CSV (2023/2024 regular seasons), MLB Stats API 2024 regular-season schedule, football-data.co.uk E0 2023–24/2024–25 CSVs. Writes `<sport>_source_<index>.bin`, `<sport>_games.csv`, and `provenance.json` under `data/raw` by default. |

There is no standalone `mlb_collector.py` in this checkout. MLB schedule retrieval
is in the downloader; parsing/adaptation is also available offline in the shared
normalizer. Its downloader excludes resumed MLB games and nonfinal/non-regular
games as an ML policy; the canonical ingestion adapter has a separate contract.
Sources/seasons above describe checked-in code, not current provider availability.
No live retrieval was performed for this handoff.

Older [refresh guidance](../../docs/DATA_INGESTION_REFRESH.md) and the
[validation checklist](../../docs/sprint3-data-validation-checklist.md) retain
NBA/UEFA wording. NBA, NHL, and Champions League code/reference rows may remain
in the repository; they are outside the official scope here.

## 3. Local file inputs and locations

The DATA-26 CLI reads local UTF-8/BOM-compatible files, never downloads them.
Select files explicitly with `--input`; multiple files share one sport and format.
There is no requirement to store imports under a particular directory.

| `--format` | Expected content | Required context / limitations |
| --- | --- | --- |
| `json` | Nonempty JSON list of canonical or collector-normalized dictionaries | Include league/source identity; raw arbitrary provider JSON is not interchangeable. |
| `csv` | Canonical/collector CSV, including NFL and football-data.org PL outputs | Include league/source and sport-required fields. Duplicate headers or wrong row widths fail. |
| `mlb-schedule` | Stats API JSON object with `dates[].games[]` | `--sport MLB`; source game IDs, date/status/team/score structure. |
| `mlb-csv` | Reduced six-column ML export | `--sport MLB`; `--season 2024` supplies missing context; often lacks kickoff and display metadata. |
| `epl-csv` | football-data.co.uk `Div=E0`, `Date`, `HomeTeam`, `AwayTeam`, `FTHG`, `FTAG` (optional `FTR`, `Time`) | `--sport EPL`; supply `--season 2023-24` or source `Season`. Date-only rows defer. |

Expected ML inputs are `data/raw/nfl_games.csv`, `mlb_games.csv`, and
`epl_games.csv`; the older reproducible pipeline also requires `data/raw/provenance.json`.
These are expected/generated locations, **not files currently available**.
See [data README](../../data/README.md). Raw/processed data is ignored by Git.

## 4. Canonical match contract and result policy

Authoritative schema: `MATCH_FIELDS` in
[multi_sport_normalizer.py](../src/normalizers/multi_sport_normalizer.py).
Every normalized dictionary exposes these fields; optional values may be `None`:

```text
game_id, sport, league, season, week, game_type, game_date,
game_time_eastern, kickoff_utc,
home_team_id, home_team_abbr, home_team_name,
away_team_id, away_team_abbr, away_team_name,
home_score, away_score, status, winner_team_id, winner_team_abbr,
location, source, neutral_site, outcome, source_season, kickoff_precision
```

- IDs are provider identities, not PostgreSQL primary keys. `game_id` and `source`
  must be valid/nonblank and fit database limits of 160 and 100 characters.
  Home/away identities must be valid and different; sport must match league.
- `game_date` is a validated calendar date; real kickoff instants use timezone-aware
  ISO timestamps normalized to UTC. Date-only precision must not become an invented
  midnight. NFL additionally requires positive `week`, a valid season year, and
  home/away abbreviations; Eastern source times account for DST.
- Completed matches require both finite nonnegative integer scores and consistent
  winner/outcome metadata. Nonfinal rows may lack scores. Season formats are
  adapted to a start year while source-season metadata can preserve the original.

| League / canonical sport | Historical result | Sprint 3 ML label policy |
| --- | --- | --- |
| NFL / `American Football` | Ties valid; no winner; winner abbreviation `TIE`. Supplied NFL outcome is checked against scores (`HOME_WIN`, `AWAY_WIN`, `TIE`); do not assume the normalizer populates `outcome`. | Binary `home_win` / `away_win`; ties excluded from targets. |
| MLB / `BASEBALL` | Completed ties rejected. Distinct source IDs preserve doubleheaders even for the same teams/date. | Binary winner labels; ML helpers exclude tied input, which does not override ingestion's rejection rule. |
| EPL / `SOCCER` | Draw valid; no winner; canonical outcome/abbreviation `DRAW`. E0 CSV adapter creates source-scoped team/match identities. | `home_win` / `draw` / `away_win`. |

Do not feed uppercase canonical outcome codes directly into lowercase ML targets
without the existing adapters. `completed` becomes database status `final`.
Recognized nonfinal statuses are sport-dependent, including `incomplete` and
`suspended` where supported. Unknown/unsupported statuses reject at normalization;
historical ingestion accepts only completed records and defers all nonfinal rows.

## 5. DATA-24 quality gate

Use `validate_historical_matches(rows)` from
[match_validation.py](../src/normalizers/match_validation.py) after raw-provider
adaptation. It runs canonical identity and sport checks plus sport normalizer
rules, returning accepted dictionaries, rejected reasons/indexes, duplicates,
and counts without mutating input or contacting a database.

Duplicate identity is exactly **`(source, game_id)`**. Identical normalized records
retain the first; conflicting valid occurrences reject the whole group in either
order. Different providers are distinct. Invalid rows are rejected independently
before grouping. `read = accepted + rejected + duplicates`.

See [DATA-24 details](historical_match_validation.md) and
[tests](../../tests/test_historical_match_validation.py). That older document has
stale NBA/UEFA and loader-policy wording; the implemented DATA-25 behavior below
and official NFL/MLB/EPL scope take precedence. The separate legacy
`data/validation.py` is not the historical quality gate.

## 6. DATA-25 persistence, references, and refresh

Use [load_historical_matches](../app/database/historical_import.py) with an
explicitly selected engine. It validates at most 1,000 input records per call,
then defers records without completed status, real kickoff, or season context.

Reference preflight requires existing sport, sport-scoped league, distinct teams,
and league-scoped season. Source team mappings are preferred and checked for sport
and target existence; fallback name/abbreviation must resolve exactly one team.
Missing or ambiguous references defer individual rows. NFL/MLB season labels are
years; EPL uses `YYYY-YY`. The importer does not create reference teams/seasons
or team mappings. [seed_data.py](../app/database/seed_data.py) contains only a
sample reference roster and does not seed seasons or full historical coverage;
it uses application configuration and is not an import-target setup command.

Within `engine.begin()`, advisory lock `491025` serializes cooperating historical
loaders. Match writes use
[upsert_match](../app/database/match_ingestion.py): source + external match mapping
selects insert versus update. Corrected scores/kickoff update the same internal ID;
identical reimports count as updates. League/team/established-season identity
changes and dangling match mappings fail. Omitted neutral-site values preserve
stored values. External provider IDs never become internal IDs directly.

Write, SQL, identity, and commit failures roll back the entire batch and report
zero committed insert/update counts. Earlier successful CLI batches remain
committed; later batches stop after failure. Only cooperating loaders share the
lock; unrelated writers are outside that concurrency guarantee. The low-level
helper requires an active transaction but does not itself run DATA-24 or acquire
the importer lock.

For exact summary semantics, reference handling, and failure policy, see
[historical import guide](historical_match_import.md). These behaviors are
implemented and mock-tested; actual PostgreSQL results remain pending.

## 7. DATA-26: runnable offline dry runs

Run from the repository root with a Python 3.12 environment containing backend
dependencies. The following complete example creates three **synthetic temporary**
JSON inputs; it uses no database or network and does not create historical datasets.
The temporary directory remains for inspecting reports or repeating commands.

```bash
cd /private/tmp/SportsBetting_491-official-normalization
export HANDOFF_SAMPLE_DIR="$(mktemp -d /tmp/sprint3-handoff.XXXXXX)"
python - <<'PY'
import json, os
from pathlib import Path
directory = Path(os.environ["HANDOFF_SAMPLE_DIR"])
for league, sport in [("NFL", "American Football"), ("MLB", "BASEBALL"), ("EPL", "SOCCER")]:
    row = dict(game_id=f"handoff-{league}-1", source="doc20-synthetic",
               sport=sport, league=league, season=2024, week=1,
               game_date="2024-09-01", kickoff_utc="2024-09-01T20:00:00Z",
               home_team_id="H", away_team_id="A",
               home_team_name="Home", away_team_name="Away",
               home_team_abbr="H", away_team_abbr="A",
               home_score=3, away_score=1, status="completed")
    (directory / f"{league.lower()}.json").write_text(json.dumps([row]))
print(directory)
PY
PYTHONPATH=.:backend:src python -m app.database.import_historical \
  --input "$HANDOFF_SAMPLE_DIR/nfl.json" --sport NFL --format json --dry-run
PYTHONPATH=.:backend:src python -m app.database.import_historical \
  --input "$HANDOFF_SAMPLE_DIR/mlb.json" --sport MLB --format json --dry-run
PYTHONPATH=.:backend:src python -m app.database.import_historical \
  --input "$HANDOFF_SAMPLE_DIR/epl.json" --sport EPL --format json --dry-run
```

Each should report read=1, accepted=1, rejected=0, duplicates=0, deferred=0,
inserted=0, updated=0 and exit 0. This checks normalization/eligibility only;
synthetic Home/Away references are not asserted to exist in any database.

For real local files, choose an existing path and use the format/context table
above. To inspect all supported arguments without opening a database:

```bash
PYTHONPATH=.:backend:src python -m app.database.import_historical --help
```

The CLI reads and validates all selected files together before batching. A dry run
does not create an engine, load records, resolve database references, or write.
JSON summaries go to stdout; timestamps/reasons/source logs go to stderr.
Exit codes: 0 success; 1 rejected/deferred records; 2 malformed input/configuration;
3 database batch failure. Accepted counts are data-quality acceptance, not stored
row counts; deferred is a subset of accepted. Inspect all detail arrays.

## 8. PostgreSQL authorization and repeatable import procedure

No PostgreSQL connection was made for DOC-20. Before future writing, explicitly
authorize a separate local import-only target and prepare its schema/reference
coverage. [Schema](../app/database/sports_prediction_schema.sql) and
[database setup](../DATABASE_SETUP_README.md) describe existing objects; their
ordinary `sports_betting` examples are not disposable-test authorization.

The import CLI requires all of: securely supplied `HISTORICAL_IMPORT_DATABASE_URL`
(or `--database-url-env NAME`), `--allow-write`, and matching `--database-name`.
URL must use PostgreSQL, loopback host, database prefix `sportsbetting_import_`,
no prod/shared/demo markers, and no query overrides. It never uses the application
default engine. These guards supplement explicit authorization; a local name
alone does not prove that a database is disposable. Do not import synthetic
examples into shared, demo, or production data. Live command syntax is in the
[DATA-26 guide](historical_match_import.md#repeatable-command-data-26).

For an authorized operator:

1. Record file checksums, source, seasons, quality counts, code revision, and the
   explicitly selected database. Dry-run the exact files first.
2. Verify complete sport/league/team/season references and provider mappings;
   resolve aliases and obtain genuine kickoff times for deferred date-only rows.
3. Run the documented CLI with `--allow-write`, matching database name, and batch
   size 1–1000. Save stdout/stderr; the CLI does not persist `ingestion_runs`.
4. Inspect rejection/defer/failure details and committed counts. After any partial
   multi-batch failure, reconcile prior commits before repeating the import.
5. Read back source-mapped matches: compare counts, source/game uniqueness,
   league/season/team joins, `final` scores, kickoff, neutral-site values and IDs.
   Repeat identical input: expect updates with unchanged match/mapping count and IDs.
   Then test a controlled correction and failure rollback in a disposable target.

Real integration tests separately require local database
`sportsbetting_data25_test`, `DATA25_DISPOSABLE_POSTGRES_URL`, and
`DATA25_ALLOW_DISPOSABLE_TEST=1`; they create/drop random schemas. They are not
authorized by ordinary application or CLI import settings. All four are currently
skipped; see [QA status](SCRUM-203-QA.md#real-postgresql-status).

## 9. ML consumers and exact contracts

| Existing consumer | Input/output and current boundary |
| --- | --- |
| [prepare_multisport_data.py](../app/ml/features/prepare_multisport_data.py) | `load_and_validate_dataset` / `validate_games`: six columns `game_id, game_date, home_team, away_team, home_score, away_score`; unique IDs per sport file, distinct teams, parseable UTC dates, finite nonnegative integer scores. This reduced contract lacks source, league, season and real kickoff guarantees. |
| [engineer_multisport_features.py](../app/ml/features/engineer_multisport_features.py) | Prior-day team history; six features: home/away win rate, average score, average allowed. Chronological split keeps whole dates together. Original target is home win versus not-home-win, including draws/ties in the latter. |
| [sport_aware_features.py](../app/ml/features/sport_aware_features.py), [train_sport_aware_baseline.py](../app/ml/training/train_sport_aware_baseline.py), [predict_sport_aware.py](../app/ml/predict_sport_aware.py) | Sprint 3 named outcomes: binary NFL/MLB and three-way EPL. Training requires all expected classes in the training partition. Inference requires six features plus `game_id`, validates probabilities, and can include model version. |
| [feature_timestamps.py](../app/ml/features/feature_timestamps.py), [kickoff_safe_features.py](../app/ml/features/kickoff_safe_features.py) | Explicit cutoff utilities require aware start/as-of/result-availability times. The kickoff-safe wrapper reuses NFL validation and prior-day binary features; it is not automatic sport-aware integration. |
| [run_multisport_pipeline.py](../app/ml/run_multisport_pipeline.py) | Existing Sprint 2 file pipeline uses three raw CSVs plus checksum-matched `provenance.json`; writes versioned models, features/train/test/prediction CSVs and evaluation reports. It remains binary, including for EPL. |
| [train_local_match_models.py](../app/ml/train_local_match_models.py) | Existing database reader `completed_games(conn, sport)` joins `matches`, `leagues`, `teams`, filters final scored matches, and projects internal match ID as `game_id`, start time as `game_date`, and team names/scores into the six-column contract. Its training command uses the configured application engine and older binary model; do not run it without explicit database approval. |

Canonical-to-ML file projection must choose stable team identities for
`home_team`/`away_team` and preserve a source-aware match key. Six-column ML
validation has no source column and will reject colliding `game_id` values.
There is no general canonical/PostgreSQL-to-Sprint-3 sport-aware export command;
agree that adapter and provenance with the ML teammate rather than assuming the
historical importer produces training CSVs automatically.

Database consumers can use `matches` joined to `sports`, `leagues`, `teams`,
`seasons`; join `external_mappings` (`entity_type='match'`) and `data_sources` to
retain provider lineage. `matches.id` is internal; provider `game_id` lives in
`external_mappings.external_id`. The importer persists kickoff, league/season/team
IDs, scores, status and neutral-site information, not every canonical field
(e.g. week, venue, precision, source-season, derived winner/outcome). Keep raw and
canonical artifacts for reproducibility. Team mappings are preexisting references;
the importer creates match mappings, not a full mapping catalogue.

Prediction API code is present, despite older ML-contract text describing API
integration as pending. [routes/predictions.py](../app/routes/predictions.py) has
two existing paths: `POST /predictions` uses
[prediction_service.py](../app/services/prediction_service.py) and a binary
home/not-home model; `POST /predictions/matches/{match_id}` uses
[match_prediction.py](../app/services/match_prediction.py), prior-day league
history and binary artifacts, splitting EPL not-home probability with a smoothed
historical draw share. Neither is the native three-class sport-aware adapter.
Do not equate the latter response with trained three-way EPL inference.
The paths also differ in history cutoff: the first uses earlier start times;
the second excludes the whole current UTC day. Neither establishes historical
result-availability timestamps by itself.

See [Sprint 3 ML contract](sprint3_ml_contract.md) for feature/probability and
artifact details, and [Sprint 2 completion evidence](../../docs/ml-planning/sprint2_completion_evidence.md)
for prior provenance/evaluation. Their historical metrics and model versions are
previous evidence, not freshly measured or necessarily available artifacts here.

## 10. Data availability, remaining work, and Sprint 4

Current `data/raw`, `data/sample`, and `data/processed` contain placeholders only;
no real NFL/MLB/EPL historical CSVs or local model build outputs were found.
Historical row counts, seasons, score completeness, duplicates, and source/team
consistency therefore remain unverified. No imported totals can be inferred.
The committed [outcome fixtures](../tests/fixtures/sprint3_match_outcomes.json)
contain NFL 3, MLB 3, EPL 4 synthetic records, with deliberate scheduled/missing
score cases. They lack source/season/team IDs and are not ingestion-ready data.
See [dataset measurements](qa/scrum203/dataset-quality.json) and QA limitations.

Recommended handoff sequence:

1. Data teammate: supply approved local historical files with checksums/source
   provenance; measure actual per-sport rows, missing fields, duplicates and seasons.
2. Database teammate: authorize a disposable target, complete reference coverage,
   run the four integration tests, and add persisted field/mapping readback evidence.
3. ML teammate: choose internal versus provider/source-scoped match and team IDs,
   build the missing explicit training projection, and keep NFL ties distinct from
   binary targets while preserving EPL draws. Avoid mixing demo and historical
   rows; current DB training queries do not filter by source.
4. Sprint 4: integrate sport-aware training/inference with one agreed API/model
   registry contract; align offline/inference cutoff policy and collect real
   result-availability timestamps. Use chronological evaluation, all expected
   classes, calibrated probability checks and trusted checksummed artifacts.
5. Track reference aliases/date-only enrichment, resumed-game policy, bounded
   input-memory behavior, durable import-run logging, and protection from unrelated
   writers as explicit follow-up work. Align older documentation/sport wording.

DOC-20 documents implemented interfaces and recorded QA. SCRUM-203 remains
partially satisfied until actual database and historical-dataset evidence exists.

## Documentation verification

For this documentation change, all 35 relative file links were checked, the 26
canonical fields were compared against `MATCH_FIELDS`, and CLI help/options were
confirmed. The synthetic command block above ran successfully: each sport read
and accepted one record, with zero rejections, deferrals, inserts, or updates.
No collectors or PostgreSQL connections were invoked. `git diff --check` and a
whitespace check of the new untracked file passed. Source/tests were unchanged;
the 488-pass QA result remains the previously committed regression evidence.
