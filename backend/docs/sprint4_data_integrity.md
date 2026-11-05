# Sprint 4 data integrity and refresh evidence

This note maps the Andrew-owned Sprint 4 data tasks to the current code and
repeatable evidence. Local fixtures are synthetic; they prove normalization and
failure behavior, not provider coverage, source accuracy, or production readiness.
No live provider refresh or PostgreSQL write was performed for this evidence.

## Source fields and checks (SCRUM-279, SCRUM-291)

| Feed | Source identity and fields | Current checks and known limits |
| --- | --- | --- |
| NFL | nflverse games CSV: game ID, season, game type, game day, teams, scores | Keep configured regular seasons, exclude missing final scores, then validate canonical ID/date/team/score fields. The six-column ML file does not retain provider ID lineage or update timestamps. |
| MLB | Stats API schedule: `gamePk`, official date, game date, game type, status, teams and scores | Keep completed regular-season games, reject missing scores, filter resumed games, collapse identical game IDs, reject conflicting duplicates. Game IDs preserve same-day doubleheaders. |
| EPL | football-data.co.uk E0 CSV: date, teams, full-time scores and season URL | Parse day-first dates as UTC, keep E0 completed rows, and validate canonical identity/team/score fields. This source lacks a stable match ID and actual kickoff time in the current adapter; generated IDs use season/date/teams and date-only records must not be treated as kickoff timestamps. |

Shared ML validation in `app.ml.features.prepare_multisport_data.validate_games`
requires nonempty unique IDs, parseable dates, distinct named teams, and finite,
nonnegative integer final scores. Missing and malformed values fail before model
feature engineering. The canonical match validator additionally checks
source-scoped IDs, sport/league compatibility, team IDs, result consistency,
timezone-aware kickoffs when supplied, and conflicting duplicate records.

The deterministic Sprint 4 normalization fixtures cover nine valid records
(three each for NFL, MLB, EPL) and three invalid examples. Additional tests cover
duplicate normalization, malformed dataset fields, ties/draws, MLB resumed games
and doubleheader identity. See `test_sprint4_pi13_normalization.py`,
`test_multi_sport_normalizer.py`, and `test_multisport_completion.py`.

## Refresh behavior (SCRUM-294, SCRUM-295–298)

Run the repeatable refresh from the repository root:

```bash
PYTHONPATH=backend:src python -m app.ml.features.download_multisport_data \
  --output data/raw --timeout 60 --retries 2 --backoff-seconds 1
```

The command retries transient HTTP and connection failures a bounded number of
times, normalizes and validates every sport before promoting outputs, and keeps
the prior files if retrieval or validation fails. Promotion stages replacements
beside the output directory and restores prior named outputs if a file replace
fails. Unrelated files in the output directory are left untouched. Errors report
the failure class and attempt count without printing the full provider URL or
exception payload. Each successful run writes source and dataset checksums plus
row counts and date bounds in `provenance.json`. The CLI is repeatable, but no
OS scheduler is installed or claimed.

Refresh unit evidence is in `test_multisport_refresh.py`: bounded retries and
backoff, sanitized terminal failure, failed validation preserving prior files,
and replacement preserving unrelated files. Tests use injected local responses;
they do not call public providers.

Verification on 2026-11-04: the focused offline command below completed with
143 passed. On this Windows host, pytest needed a repository-local `--basetemp`
because its default temporary directory was denied by filesystem permissions.

## Acceptance evidence and remaining limits

| Jira task | Local evidence | Still requires an authorized environment |
| --- | --- | --- |
| SCRUM-279, source completeness and accuracy | Required fields, missing/malformed/duplicate/out-of-range checks and repeatable offline test coverage; fixture outcomes can be recorded as expected vs actual from the test run. | Real source sample and currentness checks. The repository's raw datasets are placeholders, and the reduced six-column data has no per-record `updated_at`; age of a match is not evidence that its provider record is stale. |
| SCRUM-291, normalization | Nine expected canonical outputs and invalid fixture rejections; source IDs stay scoped and MLB doubleheaders remain separate. | Provider-specific alias coverage beyond these fixtures and a real dataset assessment. |
| SCRUM-294, reliable refresh | Bounded retries, clear sanitized failure, validation before promotion, and repeatable invocation with checksum manifest. | A real refresh should be run by an authorized operator with network access; no provider request was made for this assessment. |
| SCRUM-149 PI1.3 | PR #36 contains the replay, normalization, CLI rejection, and import evidence work. Offline fake-engine tests cover rollback; PostgreSQL test is opt-in. | Disposable local PostgreSQL setup for actual transaction rollback/reconciliation. Do not substitute demo/shared data. |

For a deterministic local run of the relevant offline coverage:

```bash
PYTHONPATH=backend:src python -m pytest -p no:cacheprovider \
  --basetemp=.pytest-sprint4-run \
  backend/tests/test_multisport_refresh.py \
  backend/tests/test_sprint4_pi13_normalization.py \
  backend/tests/test_multi_sport_normalizer.py \
  backend/tests/test_multisport_completion.py \
  backend/tests/test_historical_import.py \
  backend/tests/test_import_historical_cli.py -q
```

The PostgreSQL integration test is intentionally excluded from that command.
It requires the separately documented disposable database settings in
`historical_match_import.md`; never point it at production, shared, or demo data.
