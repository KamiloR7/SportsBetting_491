# Sprint 4 reproducible historical model training

## Scope and dependency chain

This separate contribution is on `member3/sprint4-ml-training`, in
`/private/tmp/SportsBetting_491-sprint4-training`, based on baseline commit
`8578b72`. Latest fetched main is `7b31053`. At inspection, chronological PR
[#43](https://github.com/KamiloR7/SportsBetting_491/pull/43), feature PR
[#44](https://github.com/KamiloR7/SportsBetting_491/pull/44), and baseline PR
[#45](https://github.com/KamiloR7/SportsBetting_491/pull/45) are open and unmerged.
A later stacked PR should target `member3/sprint4-baseline-predictor` until its
prerequisites merge. Existing CI filters PRs to main, so stacked PR checks may
not trigger. No Jira key is used.

Supported prediction contracts:

| League | Explicit prediction class order | Ties/draws |
| --- | --- | --- |
| NFL | home_win, away_win | Retained in history, excluded from classification fitting and evaluation targets |
| MLB | home_win, away_win | Canonical validator rejects completed tied scores |
| EPL | home_win, draw, away_win | Draws remain a separate trained class |

No NBA or UEFA/Champions League input is assumed. The older six-column training
and inference modules are unchanged. They are not compatible with the new
historical feature schema without an adapter.

## Modules and API

- `app.ml.training.historical_match_model`: `train_historical_model`,
  `HistoricalMatchModel.predict`, `save_historical_model`, `load_historical_model`.
- `app.ml.evaluation.evaluate_historical_training`: `train_and_evaluate_sport`.

The combined function returns `(model, report)` for one league. It reuses
`build_sport_feature_dataset` to generate and validate the chronological data
once, preserves the resulting split, fits a model, and compares it to both
existing historical baselines. Separate reports are required for each league;
there is no pooled cross-sport performance score.

Input records follow the canonical Sprint 3 contract with explicit source,
league, season, source-scoped match and team identities, genuine aware kickoff,
completed status, final scores, `feature_as_of` and `result_available_at`.
NFL requires week/abbreviations; EPL requires team names. The canonical adapter
and prior documentation define the exact fields. Missing availability is not
inferred from match duration, date, or kickoff. Real timestamp provenance and
archive completeness remain caller responsibilities.

The lower-level `train_historical_model(dataset, min_samples_per_class=2)`
accepts a validated `SportFeatureDataset`, not arbitrary raw provider CSVs. Direct
callers must retain the original pipeline's provenance and cutoff guarantees.
Training does not inspect test values or test labels. Each supported outcome
class must occur at least twice by default in labeled training; the threshold
may be explicitly configured to another positive integer. Missing classes,
all-tie NFL training, or inadequate sample support reject instead of silently
training a different outcome contract. One-class probability baselines remain
available independently, but do not replace multiclass model validation.

## Algorithm and preprocessing

Use the already-installed scikit-learn library (locally 1.9.1). Logistic regression
is a simple, reproducible comparator with native binary/multiclass probabilities.
NFL/MLB use binary logistic classification; EPL uses multiclass logistic
classification with all three outcomes. Configuration is explicit:

```text
solver=lbfgs, C=1.0, max_iter=1000, tol=0.0001, random_state=42
```

An iteration-limit failure rejects rather than publishing a model that did not
converge. There is no hyperparameter search, calibration, class reweighting,
resampling, or test-driven selection.

The scikit-learn Pipeline fits these transformations on **labeled training rows
only**, after preserving the original chronological boundary:

1. Median imputation with `keep_empty_features=True` and `add_indicator=True`.
2. Standard scaling with centering and variance scaling.
3. Logistic regression with the fixed configuration above.

An all-missing training column is retained and filled with zero by the imputer;
its training-derived missingness indicator makes absence explicit. This is an
explicit preprocessing fallback, not a fabricated observed statistic. Columns
missing during imputer fitting get indicator columns; newly missing test values
are imputed without refitting. No imputation statistics, scaling parameters or
classifier coefficients use test rows or NFL rows with undefined binary targets.
NFL ties still contribute to subsequent historical features through the earlier
pipeline. Their exclusion does not move the train/test boundary.

The exact ordered predictor allowlist comes from
`historical_sport_features_v1` plus sport. Metadata, dates, season identifiers,
result-availability timestamps and outcome labels are never model predictors.
NaN is permitted for unavailable rates/means, but infinite, complex, boolean and
string predictors reject. Counts must be finite nonnegative integers; rates
remain in [0,1], EPL points-per-match in [0,3], and scoring averages nonnegative.
Signed scoring margins are accepted. Imputation operates only after these
checks. Unavailable count values are invalid, not an invitation to impute counts.

## Reproducibility and prediction contract

Model family is `historical_logistic_regression_v1`. Metadata records:

- Sport, canonical class order and actual classifier class order.
- Feature schema version and exact ordered feature columns.
- Fixed training/preprocessing configuration and sample threshold.
- Labeled class counts, fitted row count, and excluded NFL ties.
- Final training UTC day and latest training result availability.
- A SHA-256 fingerprint of supplied training rows (including provenance/cutoffs).
- SHA-256 of fitted imputer/scaler state, missing-indicator columns and classifier weights.
- Exact Python, NumPy, pandas and scikit-learn versions.

The model version is a deterministic fingerprint of this training recipe,
training data and fitted numeric state. Modified coefficients or preprocessing
state cannot silently retain the recorded model identity at prediction/save time. The separate serialized artifact version/checksum identifies
exact pickle bytes. Determinism is verified locally under the same dependencies;
bitwise reproducibility across hardware, BLAS implementations or software
versions is not promised. Cross-version artifact loading is explicitly rejected.

`model.predict(frame, schema_version=...)` returns a list of dictionaries:

```text
match_id, sport, predicted_outcome, probabilities,
class_order, model_identifier, model_version, feature_schema_version
```

The model verifies metadata, feature schema/configuration and fitted pipeline
compatibility before inference. It reuses the baseline match/cutoff guards:
features precede kickoff, predictions occur after all training UTC days, and
all fitted training results are available by each prediction cutoff. Invalid
inputs reject before `predict_proba`. Named selection enforces the recorded
predictor order even when a caller's physical DataFrame column order differs.
Feature provenance must still come from the validated pipeline; timestamps do
not prove the historical truth of externally supplied numbers.

Scikit-learn's internal class order is explicitly mapped to the public order in
the table. Each output distribution passes the shared sport probability
validator: correct keys, finite values in [0,1] and total within absolute
0.000001 of one. Argmax ties use the public order, consistently with baselines.
Probabilities are uncalibrated experimental classifier outputs, not betting odds.

## Evaluation and fair baseline comparisons

Use the canonical whole-UTC-day chronological split. Features are restricted to
current-season, prior-day results available by each match's feature cutoff.
All training labels must be available by the earliest held-out cutoff. Earlier
held-out results may contribute to later held-out rolling features after their
availability; no held-out labels enter fitting, preprocessing or frozen baseline
frequencies. This is rolling evaluation, not fixed-origin multi-match forecasting.

Reuse the baseline evaluator's classification metrics for each method:
accuracy, macro precision/recall/F1, per-class support and a fixed-size confusion
matrix (rows=actual, columns=predicted). Both binary and EPL use fixed supported
class lists and zero for undefined class metrics. EPL draws are never collapsed.

Compare logistic regression, historical home frequency and team-form heuristic
on the same labeled held-out partition. The imputed model can predict cold
starts; the heuristic may lack sufficient history. Each method reports its own
coverage, predicted match IDs and missing-history reasons. **Common-cohort
metrics use exactly the intersection of match IDs predicted by all methods**,
so coverage differences cannot masquerade as performance improvements. Invalid
data aborts evaluation; only explicit insufficient-history errors are skipped.
Null metrics/coverage identify empty evaluable cohorts rather than fake zeros.
Excluded NFL test ties are separately counted.

## Persistence and trust

`save_historical_model(model, directory)` reuses the immutable project artifact
writer. It emits versioned `<sport>_baseline.pkl` and JSON metadata (the filename
is inherited from the existing writer). Repeated saves never overwrite a
different payload at an existing artifact path. Generated artifacts belong
outside tracked source; none are committed by this contribution.

`load_historical_model(path, trusted_local=True)` is an explicit trust opt-in.
Without it, deserialization is refused. The loader checks compatible metadata,
model/schema/configuration/software versions and payload SHA-256 **before**
unpickling, then checks pipeline types, fitted feature dimensions, preprocessing,
classifier classes and configuration. It reads one metadata record and one
payload, checking the same bytes that it deserializes.

**Pickle can execute code. Checksums detect accidental changes; they are not
signatures and do not establish authenticity.** Only opt in for artifacts already
verified as trusted local output with controlled access. Never opt in for user
uploads, arbitrary downloads or third-party pickle files. The flag itself is
not a trust mechanism. A compatible malicious pickle is not made safe by JSON
metadata. This is trusted-local persistence, not an untrusted-model sandbox.

Loading and reserializing can change pickle bytes while preserving predictions;
that can produce a different artifact version with the same logical model
version. Original artifacts remain immutable. Serialization and prediction
round trips are tested separately from any bitwise byte equivalence claim.

## Usage with approved data

```python
from pathlib import Path
from app.ml.evaluation.evaluate_historical_training import train_and_evaluate_sport
from app.ml.training.historical_match_model import save_historical_model, load_historical_model

# approved_records must be real canonical history with verified availability.
model, report = train_and_evaluate_sport(approved_records, "EPL")
path = save_historical_model(model, Path("/private/tmp/trusted-sport-models"))
restored = load_historical_model(path, trusted_local=True)  # trusted local output only
```

Run separately for NFL, MLB and EPL; inspect class coverage and rejection reasons
before interpreting any report. No automatic provider retrieval, PostgreSQL
training query, scheduled-match API, or deployment occurs.

## Real-data blockers and limitations

NFL, MLB and EPL historical files with verified availability provenance remain
unavailable. **Real-world training, accuracy, precision, recall, F1, calibration
and profitability evaluation are not complete.** Synthetic fixtures exercise
engineering behavior only. No historical dataset, real-world metric, or trained
production artifact was invented. Genuine source files, complete source/team
identity coverage, timestamps and provenance must be supplied before real-data
acceptance. Models inherit the feature pipeline's single-provider and quadratic
history-scan limits. PostgreSQL integration and hosted CI remain separate checks.

## Local engineering verification

- **46 new training tests passed** across binary and EPL multiclass training,
  probability/class ordering, missingness, determinism, training-only statistics,
  insufficient samples/classes, invalid inputs, leakage guards, fitted-state
  integrity, trusted artifact round trips, pre-deserialization compatibility and
  checksum rejection, and baseline comparison cohorts.
- Focused training plus dependency suites: **156 passed, 0 failed**.
- Full regression under the existing SCRUM-203 network/PostgreSQL guard:
  **665 passed, 0 failed, 4 skipped**. The four PostgreSQL integration tests need
  an explicitly configured disposable database and were not executed.
- Python compilation passed for backend/app, backend/tests, backend/src and src.
- Whitespace/final-newline checks passed for the four added files.
- No backend Python lint/type-check command is configured. Frontend ESLint is
  unrelated to this Python-only contribution.

Tests use synthetic canonical fixtures solely for engineering verification.
Synthetic classifier/metric assertions do not constitute real-data evaluation.
No model artifacts are generated into tracked source: persistence tests use
pytest temporary directories. Existing dependencies are reused through the
isolated environment `/private/tmp/sprint4-coverage-review-gk6g4rd_`; no shared
packages or tracked requirements were changed. Evidence is local, not hosted CI:
`/private/tmp/sprint4-training-focused.xml` and
`/private/tmp/sprint4-training-regression.xml`.

Reproduce focused tests from the repository root with backend dependencies:

```bash
PYTHONPATH=.:backend:src python -m pytest -q backend/tests/test_historical_match_training.py
```

This separate training contribution targets `member3/sprint4-baseline-predictor`
as a stacked PR until its prerequisites merge. Real-data acceptance, PostgreSQL
execution, and hosted CI remain unverified. This contribution implements and
test-verifies the infrastructure only; merging or modifying earlier worktrees
is outside its scope.
