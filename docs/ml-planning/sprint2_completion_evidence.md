# Sprint 2 completion evidence — Ayman Sadek

## Status and scope

The follow-up implementation has been completed and validated **locally**.
These changes are not included in already-merged PR #15 until a new reviewed
commit/PR is published. Jira statuses were deliberately left unchanged.
This report supersedes the missing-real-data statements in the original PR
validation note for this local follow-up only; it does not rewrite historical evidence.

Related work: [SCRUM-129](https://cpsc-491-group5.atlassian.net/browse/SCRUM-129),
[SCRUM-130](https://cpsc-491-group5.atlassian.net/browse/SCRUM-130),
[SCRUM-131](https://cpsc-491-group5.atlassian.net/browse/SCRUM-131),
[SCRUM-132](https://cpsc-491-group5.atlassian.net/browse/SCRUM-132).

## What was completed

| Work | Implementation and verification |
| --- | --- |
| Baseline review and real datasets | Reviewed the original NFL baseline; downloaded, normalized and validated historical NFL, MLB and EPL results. Provider bytes, source URLs, retrieval timestamp, selection/exclusion counts and SHA-256 fingerprints are recorded. |
| Features and splits | Six prior-day team-history features; no current-day or future results enter earlier features. Same-day games stay together in chronological holdout. Empty, single-row and single-date data are rejected. |
| Three sport baselines | Separate StandardScaler + LogisticRegression models, random seed 42, trained only on each training partition. Training requires both binary classes and finite features. |
| Evaluation | Held-out accuracy, precision, recall, F1, confusion matrix, Brier score, log loss, calibration bins and training-prevalence baseline comparison. No tuning on these holdouts. |
| Persistence/versioning | Sport-specific content-derived model directories; SHA-256 model verification, dataset and source fingerprints, class/feature order, split dates/counts and package versions. Existing model/metadata bytes are never silently replaced. |
| Prediction interface | Validated ordered inputs, explicit home-win/not-home-win probabilities, checksum-checked trusted model loading. Reloaded models produce exactly identical probabilities. |
| Automated verification | 105 tests pass, including an offline three-sport end-to-end workflow, dataset corruption guard, chronology/leakage, invalid values, model round-trip and immutable model versions. Python wheel build and compilation pass. |

## Real data, provenance and responsible use

- NFL: [nflverse schedules](https://github.com/nflverse/nfldata/blob/master/data/games.csv),
  completed regular-season games for 2023 and 2024; 544 rows.
  Source `gameday` maps to `game_date`; score/team/game ID columns retain their meaning.
  [Schedule field dictionary](https://nflreadr.nflverse.com/articles/dictionary_schedules.html).
- MLB: [MLB schedule API, 2024 regular season](https://statsapi.mlb.com/api/v1/schedule?sportId=1&season=2024&gameType=R),
  2,469 returned records; exclude 37 not-completed regular-season entries and
  six resumed-game entries, leaving 2,426 games. Use officialDate, gamePk,
  team IDs and final scores. Do not use final-season standings/leagueRecord.
  Resumed games are excluded so results cannot appear before they were known.
- EPL: [Football-Data historical England results](https://www.football-data.co.uk/englandm.php),
  2023/24 and 2024/25 E0 files, 380 matches each. Date is parsed day-first,
  HomeTeam/AwayTeam and FTHG/FTAG map into the shared contract; deterministic
  game IDs include season/date/teams. Odds and current-match statistics are excluded.

Provider responses and normalized rows stay in ignored `data/raw/`.
The compact provenance evidence is `sprint2_real_data_provenance.json`.
Public download availability is not a blanket redistribution license: retain
provider attribution and consult provider terms before sharing raw data or
using it commercially. This academic experiment does not authorize betting
or represent investment/gambling advice.

## Data validation and leakage controls

The shared contract requires nonblank unique game IDs, nonblank distinct teams,
ISO-8601 dates, and finite nonnegative integer final scores. Missing dates,
duplicate IDs, missing columns, empty datasets, invalid sports and malformed
scores fail explicitly. Source adapters handle completed-game filtering before
validation; no synthetic match results are substituted.

Features are expanding historical team win rate, average score and average
score allowed for each side. Cold-start teams receive zeros. Source match
calendar dates are treated as day buckets, not precise kickoff timestamps.
All games in a day are featurized before that day's scores update history;
doubleheaders cannot leak their first result into the second game's inputs.
Splits choose the closest complete-day boundary to 80/20. The actual fraction
can differ slightly; all training dates strictly precede test dates.

Evaluation is **rolling pre-game** with a fixed trained classifier: prior
held-out days' observed results may become features for later held-out days.
This is not a forecast of an entire future season with no intervening results.
The scaler is fitted only on training rows. Mutation tests check that future
scores cannot change earlier feature rows.

## Measured held-out results

| Sport | Real games | Train / test | Accuracy | Constant baseline accuracy | F1 (home win) | Brier ↓ | Log loss ↓ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| NFL | 544 | 437 / 107 | 66.36% | 53.27% | 0.7391 | 0.2218 | 0.6351 |
| MLB | 2426 | 1944 / 482 | 55.19% | 51.04% | 0.6646 | 0.2469 | 0.6868 |
| EPL | 760 | 609 / 151 | 65.56% | 56.29% | 0.5667 | 0.2101 | 0.6051 |

The constant comparison uses only the training home-win prevalence and its
majority class; it is not chosen using the test labels. All three models
outperformed that simple comparator on this one holdout, which does not prove
future superiority, calibrated betting odds or profitability. MLB improvement
is modest and predictions cluster near 0.5. EPL calibration bins reveal
over/under-confidence; tiny bins are not statistically reliable. Calibration
was **measured**, not fitted on the test set. Future calibration fitting must
use a separate training/validation partition.

- **NFL:** train 2023-09-07 through 2024-11-17; test 2024-11-18 through 2025-01-05. Model version `f35e4b52fca3d0c170e5`.
- **MLB:** train 2024-03-20 through 2024-08-24; test 2024-08-25 through 2024-09-30. Model version `1ed880eb8ce31e47452f`.
- **EPL:** train 2023-08-11 through 2025-01-26; test 2025-02-01 through 2025-05-25. Model version `8fe44dc6fa087a157dfd`.

The target is explicitly **home win (1) versus not-home-win (0)** for all
sports. EPL draws are included in not-home-win, never described as away wins.
This delivers an initial binary classifier, not a full three-way EPL market.
Three-way outcomes, stronger features, walk-forward cross-validation,
uncertainty intervals and monitored retraining are subsequent improvements.

## Reproduce locally

Run from the repository root with Python 3.12. The tested dependency snapshot
is captured in `backend/requirements-sprint2-tested.txt`; it is a record of the
tested environment, not a cross-platform lock with package hashes.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -c backend/requirements-sprint2-tested.txt -r backend/requirements.txt pytest
python -m pip install -e .
PYTHONPATH=backend python -m app.ml.features.download_multisport_data
PYTHONPATH=backend python -m app.ml.run_multisport_pipeline
PYTHONPATH=backend python -m pytest -q --junitxml=build/sprint2-tests.xml
python -m pip wheel --no-deps . --wheel-dir build/dist
```

Downloads require network access, but tests and training from cached inputs do
not. Download failure fails the command; it never substitutes sample data.
For exact historical replication, reuse the cached normalized files and their
matching provenance manifest. Mutable provider URLs may produce revised
responses on another day; compare the recorded hashes rather than claiming
identical inputs automatically.

A second complete training/evaluation run produced a byte-identical report:
`655f1b9cf6b79127ab4a5f343691aa7beff6e5e04980c4df8f189d1e2bfe3bbf`.

## Model interface and artifacts

Input: pandas DataFrame with numeric columns in this declared order:
`home_win_rate`, `away_win_rate`, `home_avg_score`, `away_avg_score`,
`home_avg_allowed`, `away_avg_allowed`. Extra columns are ignored; missing,
empty, nonfinite or negative inputs are rejected and win rates must lie in [0,1].

```python
from pathlib import Path
from app.ml.predict_multisport import load_trusted_baseline, predict_outcomes

model, metadata = load_trusted_baseline(Path("build/sprint2-models/SPORT-VERSION/SPORT_baseline.pkl"))
predictions = predict_outcomes(model, pregame_features)
```

Replace SPORT-VERSION with an actual directory from report.json (sport prefixes
are lowercase). Output preserves the input index and contains
`predicted_outcome`, `probability_not_home_win`, `probability_home_win`.
The two probabilities correspond to classifier classes [0, 1] and sum to one.
Use feature generation from observed historical results before supplying
pregame values. This library interface is not an already-deployed HTTP endpoint.

Each version directory contains the pickle, metadata JSON, evaluation JSON,
features/train/test CSVs and held-out predictions. Models and raw data are not
checked into Git; compact metric/provenance JSON evidence is suitable for review.
Only deserialize trusted local artifacts: a hash beside an untrusted pickle
does not make the pickle safe.

Source identity for this local evidence:
`0af9f4ded7edfe42f5a67a6ffd537924b6d33c751a08347ebd35f0f75972f404`.
Metadata explicitly records uncommitted ML changes relative to Git HEAD
`9e1e1f781d2f2de9bf7ddf3adfd47e52eca897cf`; it does not pretend this code is in PR #15.
The version derives from model bytes and metadata (including dataset/source
fingerprints), not only a timestamp or row count.

## CI, review and Jira handoff

The follow-up CI preserves PR-to-main and push-to-main triggers. It uses the
tested dependency constraints, builds a Python wheel, compiles Python, executes
the offline test suite and uploads test results plus versioned build metadata
and wheel output. IDs include run number, run attempt and short commit SHA.
The wheel packages the existing src collector distribution; it is not a
packaged backend deployment or a trained-model archive.

Existing [PR #15](https://github.com/KamiloR7/SportsBetting_491/pull/15) was merged,
and [CI run #22](https://github.com/KamiloR7/SportsBetting_491/actions/runs/36957868066)
passed for the earlier implementation. Those links do **not** certify the new
local changes. Publish this follow-up for teammate review, verify the new
GitHub-hosted run, and link its PR/run before marking tickets Done under the
team's review/merge policy. No Jira status was changed during this completion work.

Each teammate still supplies their own automation/test contribution and ticket
evidence. This work does not claim their contribution or change their tickets.
