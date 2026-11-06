# Sprint 4 chronological dataset foundation

This change proceeds without a Jira issue key, as authorized by Kamilo Ramirez.
Proposed identifiers are not treated as verified Jira keys.

`app.ml.features.chronological_dataset.build_chronological_dataset(records,
sport, test_fraction=0.2)` projects canonical Sprint 3 records into validated
training and test DataFrames. Run from the repository root with
`PYTHONPATH=.:backend:src`. The returned object exposes `train`, `test`, and `sport`.
This is an offline library; it does not query PostgreSQL or retrieve providers.

## Input and leakage policy

- Supported leagues are NFL, MLB, and EPL, matching the implemented Sprint 3
  contract. NBA and UEFA/Champions League training are outside that contract.
- Supply canonical match dictionaries accepted by `validate_historical_matches`,
  with season, completed status, real aware `kickoff_utc`, and two additional
  verified timestamps: `feature_as_of` and `result_available_at`. Season must be
  explicitly supplied as `season` or `source_season`; the MLB normalizer
  fallback that infers a year from the date is insufficient provenance.
- Availability timestamps must come from actual provenance. Kickoff, calendar
  date, and a guessed match duration are not evidence of result availability.
- Invalid records and both identical and conflicting duplicates reject the batch.
  Mixed leagues and multiple providers reject; cross-provider match/team alias
  resolution is not implemented. This avoids counting provider copies twice.
- Match keys and team keys are collision-safe JSON tuples scoped to source (and
  league for teams). The original match key, source, season, sport, real kickoff,
  source-season label, and availability timestamps are retained alongside the
  reduced ML fields. `source_season` can be null when the existing normalizer
  provides no separate source label (for example NFL).
- Split by UTC kickoff day using the existing nearest whole-date boundary. The
  requested fraction is approximate; equal-distance boundaries choose the earlier
  one. At least two distinct UTC kickoff dates are required.
- All training labels must be available by the earliest test feature timestamp.
  Every prior-day result involving a team must be available at that match's
  feature cutoff; this also covers rolling history within the test partition.
  Features must precede kickoff and results must follow kickoff strictly.

The returned frames contain final scores for target construction and historical
aggregation. They are **not prediction feature matrices**. Use explicit feature
allowlists, never all numeric columns. This change creates no new feature schema
or model version and changes no existing training/API behavior. Sport-aware
feature generation and a runnable training integration remain separate work.
The availability rule matches prior-day rolling evaluation; it does not implement
fixed-origin forecasting or refit a model on held-out labels. Earlier held-out
results may contribute to later held-out features only after availability.
History includes all earlier UTC days, including earlier seasons, matching the
existing feature generator; there is no new rolling window or seasonal reset.
An unavailable candidate result rejects the dataset rather than silently
changing the established history-selection policy. Timestamp values are checked
for ordering and awareness; their factual provenance must be verified by the
caller. This builder cannot prove when a provider originally published a result.

## Data blocker and validation

No real historical files or verified availability timestamps were available in
this checkout. No dataset, trained model, accuracy, calibration, or freshness
claim is produced. Supply approved canonical history and timestamp provenance
before real-data execution. Missing availability fails closed.

Tests use explicitly synthetic canonical records. They cover all three leagues,
input order determinism, whole-day partitions, invalid/missing timestamps,
duplicate integrity, delayed training labels, rolling-test leakage, mixed
sources/leagues, and independence of training rows from test score changes.


## Acceptance criteria review

| Criterion | Evidence |
| --- | --- |
| Training dates strictly precede test dates | Existing whole-date splitter, including earlier-boundary tie behavior |
| Fitted labels exist before test predictions | Latest training availability checked against earliest test feature cutoff; equality allowed |
| Training and rolling test history use eligible results | Prior-day team-result availability checked against each match's feature cutoff |
| Future and same-day results cannot affect earlier features | Feature invariance and same-day exclusion regression tests |
| Source and season survive projection | Source-scoped keys, original game ID, explicit normalized season and source label retained |
| Invalid data fails before training | Sprint 3 gate plus timestamp, status, provider and season checks |
| Deterministic supported-sport output | Reversed-input equality tests for NFL, MLB and EPL; original inputs unchanged |

NFL ties and EPL draws remain scored records for downstream sport-specific
labeling. MLB completed ties are rejected by the reused canonical contract.
No model fitting or prediction execution occurs in this module.

## Verification results

Reviewed against `origin/main` at `7b31053`. All **38 dataset tests passed**.
Full offline regression with the existing SCRUM-203 network/PostgreSQL guard:
**547 passed, 0 failed, 4 skipped**, including both coverage-reporting tests.
The four PostgreSQL integration tests require a separately configured disposable
database and were not exercised. No network or PostgreSQL connections were made
by the guarded run.

CI explicitly installs `pytest-cov>=7,<8`; backend/requirements.txt also declares
pytest-cov. The earlier two local coverage failures were resolved by installing
pytest-cov 7.1.0 and coverage 7.17.2 into the isolated temporary virtual environment
`/private/tmp/sprint4-coverage-review-gk6g4rd_`. Existing backend dependencies are
reused read-only through a temporary site-packages path. The shared environment
and tracked dependency files were unchanged. Both previously failing tests passed
individually (2 passed), then passed as part of the full suite.

Python compileall passed for backend/app, backend/tests, backend/src, and src.
No backend lint or type-check command is configured. JUnit evidence is local at
`/private/tmp/sprint4-final-with-coverage.xml`; it is not a committed or CI artifact.
The full regression includes the ingestion, refresh, and normalization changes
from latest main. Historical pre-synchronization test counts are superseded by
this result.

Reproduce the dataset tests from the repository root with backend dependencies:

```bash
PYTHONPATH=.:backend:src python -m pytest -q backend/tests/test_chronological_dataset.py
```

The foundation's synthetic contract criteria pass and it is ready for commit
and peer review. Proceeding without a Jira key is authorized by Kamilo Ramirez. Real-data acceptance is
still blocked by missing historical files and verified availability provenance.
PostgreSQL integration and hosted CI verification remain pending; neither is
claimed as passed.
