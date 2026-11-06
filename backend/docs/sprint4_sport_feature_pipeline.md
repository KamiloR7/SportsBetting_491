# Sprint 4 sport-aware historical feature pipeline

## Scope and dependency

Implementation lives in `app.ml.features.historical_sport_features`. Supported
leagues are NFL, MLB and EPL, matching the actual normalized data contracts.
NBA and UEFA/Champions League data are not assumed available.

This work is on `member3/sprint4-feature-engineering` in the separate worktree
`/private/tmp/SportsBetting_491-sprint4-features`, based on chronological commit
`99210e8`. At inspection, latest `origin/main` was `7b31053` and lacked that
commit/module. This is a dependent branch, not a replacement for the chronological
PR. Until the prerequisite merges, compare against
`member3/sprint4-chronological-dataset` for the feature-only review. Recheck the
base before opening a PR against main so the prerequisite is not reviewed twice.
The GitHub API confirmed chronological PR
[#43](https://github.com/KamiloR7/SportsBetting_491/pull/43) is open and unmerged.
The intended stacked PR targets `member3/sprint4-chronological-dataset`.
Current CI filters pull requests to `main`, so the stacked PR may not trigger
those checks until retargeted after the prerequisite merges. Do not treat local
regression evidence as hosted CI results.
No Jira identifier is used in this branch or suggested PR title.

## Public functions and input

`build_sport_feature_dataset(records, sport, test_fraction=0.2)` returns a
`SportFeatureDataset` containing `train`, `test`, `sport`, `feature_columns`, and
`schema_version`. `feature_columns(sport)` returns a fresh, ordered predictor
allowlist. Schema version: `historical_sport_features_v1`; sport and the exact
allowlist must also be stored with any future model artifact.

Input records are canonical Sprint 3 match mappings enriched with genuine aware
`feature_as_of` and `result_available_at` timestamps. They require source/game/team
identity, selected league, an explicit season, completed status, final scores,
and genuine aware kickoff. Refer to the chronological dataset contract for
sport-specific fields (NFL week/abbreviations, EPL team names, etc.).
`source_season` can supply season context where the canonical normalizer supports
it; an MLB calendar-year fallback is not accepted as explicit provenance.

The pipeline reuses `build_chronological_dataset`, the canonical integrity gate,
existing cutoff validators, and `label_match_outcome`. Empty inputs, incomplete
scores, duplicates, mixed providers/leagues, missing timestamps, and invalid
cutoffs reject before feature calculation. At least two distinct kickoff UTC
dates are required. Input dictionaries are not mutated.

## Historical selection and leakage policy

For each target match:

1. Match the target's normalized season and source-scoped team identities.
2. Include only earlier UTC kickoff days. The entire current UTC day is excluded,
   even if an earlier game has already finished.
3. Include only results available at or before the target `feature_as_of`.
4. Order eligible matches by actual kickoff, then source-scoped game key, before
   taking the last 5 or 10. This preserves doubleheader ordering. Equal kickoff
   instants have deterministic game-key ordering.

The prerequisite validator rejects a target team's prior-day result that is not
available by that target's cutoff; results are not silently removed to make
its direct form look valid. That strict validation runs before season filtering,
so it can conservatively reject delayed prior-season results too. For opponent
strength, games involving other teams also pass the availability filter; an
unavailable indirect result cannot affect the opponent's rate.

All training labels must be available by the earliest test feature cutoff.
The original approximate 80/20 whole-day split and earlier-boundary tie-breaking
are retained. No scaler, imputer, model, or calibration is fitted here.
Earlier held-out results may enter later held-out feature history after their
availability, but never model fitting: this is rolling historical evaluation,
not fixed-origin forecasting. Results of the target and future matches cannot
enter its features. Timestamp truth must be verified by the caller; ordering
checks do not prove when a provider published a result or correction.

## Feature definitions

Every predictor is prefixed `home_` or `away_` for the team in that role in the
target match. All statistics reset at season boundaries, including recent form
and opponent strength. There is no cross-season fallback. Within a scope of
eligible team games, let `n` be games played, `W` wins, `L` losses, and `D` tied
scores. Ties/draws remain in history, not losses.

| Fields after the team prefix | Definition |
| --- | --- |
| `season_matches`, `season_wins`, `season_losses` | Counts over all eligible current-season matches |
| `season_ties` (NFL only) | Eligible tied NFL matches |
| `season_draws` (EPL only) | Eligible drawn EPL matches |
| `season_points_per_match` (EPL only) | `(3*W + D) / n` |
| `season_win_rate` | `W / n` |
| `season_avg_scored`, `season_avg_conceded` | Mean team score and opponent score |
| `season_avg_margin` | Mean `(team score - opponent score)`; negatives are valid |
| `recent5_matches`, `recent10_matches` | Available observations, capped at 5 or 10 |
| `recent5_win_rate`, `recent10_win_rate` | Win fraction over the last available 5 or 10 games |
| `recent5_avg_scored`, `recent10_avg_scored` | Mean team score in that window |
| `recent5_avg_conceded`, `recent10_avg_conceded` | Mean opponent score in that window |
| `recent5_avg_margin`, `recent10_avg_margin` | Mean scoring margin in that window |
| `venue_matches`, `venue_win_rate`, `venue_avg_scored`, `venue_avg_conceded`, `venue_avg_margin` | Same summaries for previous home games of the target home team, or previous away games of the target away team |
| `opponent_win_rate` | Mean current-season win fraction of previously faced opponents, using their available games against teams other than the focal team |
| `opponent_observations` | Number of prior encounters contributing a known opponent rate |

Opponent strength is encounter-weighted: an opponent faced twice contributes
twice if its external history is known. Opponents with no eligible games against
other teams contribute nothing, and the observation count makes this explicit.
It uses raw outcomes, not recursively computed opponent ratings.

Win rates are literal observed wins divided by completed games. NFL ties count
in the denominator without half-win credit; this is not the NFL standings
percentage. EPL draw rates affect points-per-match and draw counts rather than
being relabeled as away wins. Scoring means stay in native points (NFL), runs
(MLB), or goals (EPL); scores across sports are never pooled.

## Output schema and missing values

Frames contain, in order:

- Metadata: `game_id`, `source_game_id`, `source`, `season`, `source_season`,
  `sport`, `game_date`, `start_time`, `feature_as_of`, `result_available_at`,
  `home_team`, `away_team`. `game_date` is the split's UTC day; `start_time`
  retains actual kickoff. Provider/league-scoped keys survive projection.
- Ordered numeric predictors from `feature_columns(sport)`.
- `outcome`: `home_win`/`away_win`, plus `draw` for EPL. NFL ties have a missing
  binary target (`None`/pandas null); preserve them in history and exclude them
  from a future binary model's fitting/evaluation targets. Canonical validation
  rejects completed MLB ties.

With no eligible history, counts are zero and rates/means are `NaN`, not invented
neutral values. Partial recent windows use the available games, with their count;
a count below 5/10 explicitly identifies insufficient full-window history.
Missing external opponent history similarly yields zero observations and `NaN`.

Never pass all numeric columns into a model: metadata includes season and labels
carry post-match information. The predictor allowlist excludes all metadata,
result timestamps and labels. This schema differs from the existing six-column
Sprint 3 schema: it includes missing values and signed margins. Existing baseline
training/prediction modules are unchanged and are not compatible with this schema
without a separately versioned training adapter.

A future model must select this exact allowlist, fit imputation/scaling on the
training partition only, and persist sport, schema version, feature order, missing
value policy, and outcome classes. It must preserve the validated split instead
of resplitting after dropping unlabeled ties.

```python
from app.ml.features.historical_sport_features import build_sport_feature_dataset

# records must be approved canonical historical records with verified timestamps.
dataset = build_sport_feature_dataset(records, "EPL")
X_train = dataset.train.loc[:, dataset.feature_columns]
y_train = dataset.train["outcome"]
X_test = dataset.test.loc[:, dataset.feature_columns]
# No fitting or imputation happens implicitly.
```

## Limitations and evidence boundaries

No real historical files or verified availability provenance were available.
No model training, real-data accuracy, calibration or betting-quality claim is
made. This API builds completed historical training/evaluation rows; scheduled
match inference integration is separate work. There is no live database or
provider retrieval, cross-provider alias resolution, missing-record discovery,
lineup/injury/weather/possession data, or inferred scoring statistics.

Venue means assigned home/away role; neutral-site geography is not modeled.
Season state uses the normalized league season, not calendar-year resets inferred
from kickoff. Counts describe supplied eligible history, not proof of a complete
provider archive. Missing games require a separately verified source inventory.
The in-memory per-target history scan is quadratic in match count; large archives
have not been benchmarked. No model artifact or deployment is changed.

## Verification

Run from the repository root with backend dependencies and CI-required
`pytest-cov>=7,<8` available:

```bash
PYTHONPATH=.:backend:src python -m pytest -q \
  backend/tests/test_historical_sport_features.py \
  backend/tests/test_chronological_dataset.py
```

Tests use synthetic canonical records only. They cover exact window/scoring
formulas, venue selection, season reset, EPL draws/points, NFL ties, doubleheaders,
new teams, partial history, opponent support/availability, chronological splits,
future-score invariance, malformed inputs, determinism and input immutability.

Verified locally on this dependent branch:

- Feature plus chronological suites: **64 passed** (26 new feature tests and
  38 prerequisite dataset tests).
- Full regression under the existing SCRUM-203 network/PostgreSQL guard:
  **573 passed, 0 failed, 4 skipped**. All four skips are PostgreSQL integration
  tests requiring a separately configured disposable database.
- Python compilation passed for backend/app, backend/tests, backend/src and src.
- Whitespace/final-newline checks passed for the three added files.
- No Python lint/type-check command is configured in the repository. The frontend
  ESLint command is unrelated to this Python-only change.

The existing isolated environment
`/private/tmp/sprint4-coverage-review-gk6g4rd_` supplied coverage tooling; shared
dependencies and tracked requirements were unchanged. Full JUnit evidence is
`/private/tmp/sprint4-features-regression.xml` (temporary local evidence, not
hosted CI). Real-data acceptance, PostgreSQL execution, and hosted CI remain
unverified. These local results do not claim hosted CI execution.
