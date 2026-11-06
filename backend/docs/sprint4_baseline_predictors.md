# Sprint 4 historical match baselines

## Scope and dependencies

Supported leagues are NFL, MLB and EPL. There is no assumed NBA or UEFA/Champions
League dataset. Latest fetched main was `7b31053`. GitHub confirmed chronological
PR [#43](https://github.com/KamiloR7/SportsBetting_491/pull/43) and feature PR
[#44](https://github.com/KamiloR7/SportsBetting_491/pull/44) were open and unmerged.
This contribution is a separate dependent branch:
`member3/sprint4-baseline-predictor`, based on feature commit `ef5235d` in
`/private/tmp/SportsBetting_491-sprint4-baselines`. Review against
`member3/sprint4-feature-engineering` until the prerequisites merge. No Jira key
is used. Main, prior worktrees, and stashes are not changed.

The existing Sprint 2 frequency comparator and Sprint 3 logistic regressions use
the older six-feature/binary evaluation contract. They are preserved. These
baselines reuse the new historical schema, outcome labeling, canonical validation,
chronological split, availability checks, and sport probability validator rather
than extending the old evaluator's binary assumptions or resplitting its data.
No classifier, scaler, or model artifact is trained or serialized by this change.

## Baseline A: historical home-outcome frequency

Fit on the **training partition only**. Count home wins, away wins, and EPL draws
as home-side outcomes over the supplied league's completed training matches.
For each class `c`, `P(c) = count(c) / labeled_training_matches`.

This is a league-level empirical frequency over training home-team results,
not a team-specific home-field rating. Probabilities are frozen for all held-out
matches. All explicit training seasons are pooled for this simple comparator;
it does not estimate current-season league drift. There is no smoothing,
imputation, neutral prior, or requirement that every class be observed. An absent
training class has probability zero. Small samples can produce overconfident
probabilities; they are not claimed to be calibrated.

NFL ties are excluded from binary counts and reported separately. NFL and MLB
probabilities are over home/away wins; NFL output is conditional on a decisive
result, not an estimate of tie probability. EPL draws remain their own class.
A minimum of one labeled training match is required by default; callers may
increase `min_training_matches`. An empty/all-tie NFL training history raises
`InsufficientHistoryError`, rather than counting ties as away wins.

## Baseline B: deterministic team-form heuristic

Use the ordered `historical_sport_features_v1` contract and its current-season
counts and last-five scoring statistics. For each side:

- `N` = completed current-season matches; `W` = wins; `T` = NFL ties or EPL draws
  (zero for MLB).
- Adjusted season form `R = (W + 0.5*T) / N` gives tied scores neutral credit.
- `S`, `C`, `M` = recent-five average scored, conceded and scoring margin.

Combine home/away differences without fitting weights:

```text
scale = max(1, S_home + C_home + S_away + C_away)
margin_contrast = (M_home - M_away) / scale
signal = ((R_home - R_away) + margin_contrast) / 2
q_home = (1 + signal) / 2
```

Validated counts and nonnegative scoring averages bound `signal` to [-1, 1].
The scale normalizes within the sport's native scoring units; it never pools
points, runs, and goals across leagues. Scores need not share a sport-wide scale.
Season form and normalized recent scoring contrast each receive equal weight.

NFL/MLB: `P(home_win)=q_home`, `P(away_win)=1-q_home`.

EPL: use the frozen training draw frequency `d`, not any held-out outcome rate:

```text
P(draw) = d * (1 - abs(signal))
P(home_win) = (1 - P(draw)) * q_home
P(away_win) = (1 - P(draw)) * (1 - q_home)
```

Draw probability is greatest for equal team strength and decreases as the
heuristic separates them. A training sample with no draws produces zero draw
probability even though the class remains supported. These are reproducible
heuristic probabilities, not fitted/calibrated estimates of true match odds.

The default `min_team_matches=1` requires observed history for both teams;
callers can require more. The recent window must contain `min(5,N)` observations.
The heuristic uses its available partial window and never fills missing means.
Cold starts raise `InsufficientHistoryError`. Invalid numeric values, negative
counts/scoring averages, nonintegral/inconsistent counts, and a margin that
conflicts with scored-minus-conceded reject as invalid inputs. Negative margins
are valid. Unused schema features, such as missing opponent strength, need not
be imputed for either baseline.

## Input and output contracts

`BaselinePredictor.fit(dataset, min_training_matches=1, min_team_matches=1)`
accepts a validated `SportFeatureDataset`. It checks the sport, exact declared
feature allowlist/order and schema version, labeled training outcomes, identities,
and aware timestamps. It does not inspect test outcomes. It stores immutable
class counts, the final training UTC day, latest training result availability,
and excluded NFL training ties. Call `fit`, not the dataclass constructor, to
create a validated baseline.

`predict(frame, method, schema_version=...)` accepts a nonempty frame with unique
columns and match IDs plus sport, game_date, aware start_time and feature_as_of.
Use `historical_home_frequency` or `team_form` as the method. Frequency prediction
does not require team features; form prediction requires the named fields used
above. Physical DataFrame column order does not affect named calculations.
The explicit schema version must match. Future model adapters must persist feature order as well as schema version;
this baseline validates the declared allowlist at fit time.

Each returned dictionary includes:

```text
match_id, sport, predicted_outcome,
probabilities (home_win / away_win, plus draw for EPL),
baseline_method, feature_schema_version, baseline_version
```

`baseline_version` is `historical_baselines_v1`. Every distribution passes the
existing sport validator: finite values in [0,1], correct class keys and total
within absolute tolerance 0.000001. Argmax ties resolve in fixed order
home_win, draw (EPL only), away_win. This is an explicit deterministic tie-break,
not evidence of home advantage.

## Chronological evaluation and leakage protection

`evaluate_baselines(records, sport, test_fraction=0.2, ...)` builds the canonical
chronological feature dataset once, fits frequencies once, then evaluates test
rows. No random split, test-label refit, or split after dropping ties occurs.

The prerequisite dataset/feature builders enforce:

- Explicit source/season provenance and verified availability timestamps.
- Whole-UTC-day training/test separation, with features before kickoff.
- Training labels available by the earliest held-out prediction.
- All historical team statistics from prior UTC days and available results only.
- Current-season feature reset, target-day exclusion and deterministic ordering.

Predictions also reject matches on/before the final training UTC day, or cutoffs
before the latest training result availability. Inputs must originate in the
validated feature pipeline: timestamp checks alone cannot verify the factual
provenance of arbitrary externally supplied statistics. Correction/publication
history remains a caller responsibility.

Held-out feature generation uses earlier available held-out results as rolling
history. Training frequencies and heuristic constants never update from those
labels. This is rolling evaluation, not fixed-origin multi-match forecasting.

Each method reports accuracy, **macro** precision/recall/F1 with fixed class
order and `zero_division=0`, per-class scores/support, and a fixed-size confusion
matrix (rows=actual, columns=predicted). Macro averaging includes all supported
classes, even if absent from a particular held-out sample. Binary methods use
home_win/away_win; EPL uses home_win/draw/away_win.

Reports include training/test counts, excluded NFL ties, evaluated rows,
missing-history reasons, coverage over labeled test rows, and prediction records.
Only insufficient history is skipped; malformed data aborts evaluation. Metrics
and coverage are null if there are no evaluable labels, and metrics are null if
a method predicts none. Common-cohort metrics use the intersection of match IDs
predicted by both methods, avoiding misleading comparisons with different
cold-start coverage. Future trained models should use that same validated split,
class order, available-information policy and comparison cohort, and report
coverage alongside any apparent metric improvement.

Run separately per supported league; no cross-sport pooled scores are computed:

```python
from app.ml.evaluation.evaluate_historical_baselines import evaluate_baselines

# records_by_sport must contain genuine approved canonical historical records.
reports = {
    sport: evaluate_baselines(records_by_sport[sport], sport)
    for sport in ("NFL", "MLB", "EPL")
}
```

## Real-data evaluation status and limitations

| Sport | Actual historical evaluation |
| --- | --- |
| NFL | Blocked: no historical files with verified availability provenance |
| MLB | Blocked: no historical files with verified availability provenance |
| EPL | Blocked: no historical files with verified availability provenance |

No accuracy, precision, recall, F1, calibration, or profitability results for real
sports data are claimed. Test fixture metrics are synthetic behavioral checks
only. No datasets are downloaded or invented. The evaluator is an offline
library, not a scheduled-match API, and does not query PostgreSQL. Models remain
experimental comparators with no claim of calibrated betting probabilities.
Feature generation inherits the in-memory quadratic history scan. Availability
and historical archive completeness need external evidence. Hosted CI and real
PostgreSQL integration are separate verification steps.


## Local verification

- **46 new baseline tests passed**.
- Baseline, feature and chronological suites together: **110 passed**.
- Full regression under the existing SCRUM-203 network/PostgreSQL guard:
  **619 passed, 0 failed, 4 skipped**. All four skips require an explicitly
  configured disposable PostgreSQL integration target; they were not executed.
- Python compilation passed for backend/app, backend/tests, backend/src and src.
- Whitespace and final-newline checks passed for the four new files.
- No backend Python lint or type-check command is configured. Frontend ESLint is
  unrelated to these Python-only changes.

Tests use the existing isolated coverage-enabled environment at
`/private/tmp/sprint4-coverage-review-gk6g4rd_`. No shared dependencies or tracked
requirements were changed. Evidence is local, not hosted CI:
`/private/tmp/sprint4-baseline-focused.xml` and
`/private/tmp/sprint4-baseline-regression.xml`.

Reproduce focused tests from the repository root with backend dependencies:

```bash
PYTHONPATH=.:backend:src python -m pytest -q backend/tests/test_historical_baselines.py
```

No code in earlier contributions was modified. The separate baseline
contribution targets `member3/sprint4-feature-engineering` as a stacked PR
until its prerequisites merge. Existing CI filters PRs to main, so hosted
checks may not trigger for the stacked base. No merge or next ML task is
authorized as part of preparing this contribution for review.
