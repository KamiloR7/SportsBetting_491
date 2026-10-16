# Vigor — Sprint 3 Machine Learning Contract

## Overview

This document describes the Sprint 3 Machine Learning training, inference, and proposed backend integration contract for NFL, MLB, and EPL match predictions.

**Implementation status:** Sport-aware model training, probability inference, and model artifact versioning have been implemented and tested locally.

**Backend integration status:** Final API integration and teammate review are pending.

**Scope clarification:** The original Sprint 3 roadmap referenced NBA, NFL, and UEFA. The current implemented model scope is NFL, MLB, and EPL. This change should be confirmed with the team and reflected in Jira.

## 1. Supported Prediction Outcomes

| Sport | Prediction type | Outcome classes |
|---|---|---|
| NFL | Binary | `home_win`, `away_win` |
| MLB | Binary | `home_win`, `away_win` |
| EPL | Three-way | `home_win`, `draw`, `away_win` |

Every prediction must produce finite probabilities between 0 and 1. Probabilities must sum to 1, allowing for floating-point tolerance.

For NFL and MLB, tied games are excluded from binary winner training labels.

For EPL, draws are retained as their own class.

## 2. Model Input Contract

### 2.1 Historical Training Data

| Field | Type | Requirement |
|---|---|---|
| `game_id` | String | Required unique match identifier |
| `game_date` | Datetime | Required match date |
| `home_team` | String | Required |
| `away_team` | String | Required |
| `home_score` | Integer | Required nonnegative final score |
| `away_score` | Integer | Required nonnegative final score |

Training data is validated using `prepare_multisport_data.py`.

The sport-aware feature adapter generates outcome labels and six historical prediction features.

### 2.2 Prediction Features

| Feature | Type | Requirement |
|---|---|---|
| `home_win_rate` | Number | Historical home-team win rate, 0–1 |
| `away_win_rate` | Number | Historical away-team win rate, 0–1 |
| `home_avg_score` | Number | Nonnegative historical average |
| `away_avg_score` | Number | Nonnegative historical average |
| `home_avg_allowed` | Number | Nonnegative historical average |
| `away_avg_allowed` | Number | Nonnegative historical average |

The local prediction adapter also requires `game_id`, which maps to `match_id` in its output.

Missing, nonfinite, negative, or otherwise invalid prediction features are rejected. Win rates must not exceed 1.

### 2.3 Proposed Backend Integration Fields

| Field | Requirement |
|---|---|
| `match_id` | Unique match identifier mapped from the ML `game_id` |
| `sport` | `NFL`, `MLB`, or `EPL` |
| `start_time` | Timezone-aware match kickoff/start timestamp |
| `feature_as_of` | Timezone-aware timestamp before match start |
| `home_team` | Home team identifier |
| `away_team` | Away team identifier |

The backend must provide or generate the six prediction features from information available before match start.

The existing timestamp-validation utilities enforce cutoff rules when explicitly called. The new sport-aware prediction adapter does not independently enforce `start_time` or `feature_as_of`; this validation must be integrated into the backend prediction workflow.

## 3. Prediction Response Contract

An EPL prediction response has this structure:

| Field | Example |
|---|---|
| `match_id` | `EPL-001` |
| `sport` | `EPL` |
| `predicted_outcome` | `away_win` |
| `probabilities.home_win` | `0.25` |
| `probabilities.draw` | `0.23` |
| `probabilities.away_win` | `0.52` |
| `model_version` | `c86c6a2e18c1c601a90c` |

The example probabilities are illustrative.

The predicted outcome corresponds to the highest returned probability.

The current `predict_sport_aware()` function accepts a trained model, feature DataFrame, sport, and optional `model_version`. Production backend integration should supply the model version from verified artifact metadata and include it in the response.

## 4. Missing and Invalid Data Policy

- Reject unsupported sports.
- Reject training data missing required game identifiers, teams, dates, or final scores.
- Reject invalid or negative final scores.
- Reject prediction inputs with missing or invalid feature values.
- Exclude scheduled, live, postponed, or cancelled games from completed-match outcome labels.
- Exclude tied NFL and MLB games from binary winner training targets.
- Preserve completed EPL draws as the `draw` class.
- Require chronological training/test splits.
- Require historical features to be calculated without using future match results.
- Require feature timestamps to precede match start when processing timestamped provider data.

The existing historical feature generator uses prior-day team history. Additional validation is required when integrating provider records with precise kickoff and result-availability timestamps.

## 5. Training Approach

The Sprint 3 sport-aware models use:

- Logistic Regression
- StandardScaler
- Fixed random seed: `42`
- Chronological approximately 80/20 training/test split, grouped by whole match dates
- Six historical team-performance features
- Separate classifiers for NFL, MLB, and EPL

The existing Sprint 2 training pipeline remains available and unchanged.

Sprint 3 uses named outcome labels rather than treating EPL draws as away wins.

## 6. Historical Model Evaluation

All three models were trained and evaluated locally using historical match datasets.

| Sport | Total matches | Training matches | Test matches | Holdout accuracy |
|---|---:|---:|---:|---:|
| NFL | 544 | 437 | 107 | 66.36% |
| MLB | 2,426 | 1,944 | 482 | 55.19% |
| EPL | 760 | 609 | 151 | 54.30% |

NFL and MLB were evaluated as two-class prediction problems. EPL was evaluated as a three-class problem.

Each model successfully produced the required number of probability columns, and the resulting probabilities summed to approximately 1.

These are initial historical holdout results. They do not establish production accuracy, betting profitability, or probability calibration.

## 7. Model Artifacts and Versioning

Model artifacts are saved using the existing `save_baseline()` implementation and loaded using `load_trusted_baseline()`.

Saved artifacts include a serialized classifier, metadata, checksum, and version identifier.

Verified local artifact versions:

| Sport | Artifact version |
|---|---|
| NFL | `05998ba2af32c6a16a38` |
| MLB | `3da9058ab11ba3dd0056` |
| EPL | `c86c6a2e18c1c601a90c` |

Local output directory: `build/sprint3-sport-aware-models/`

The model loader verifies the artifact checksum before loading the model. Only locally generated, trusted pickle files should be loaded.

These version identifiers refer to the locally generated artifacts and may change if the model, training data, dependencies, or metadata change.

## 8. Relevant Source Files

**Feature engineering and validation**

- `backend/app/ml/features/prepare_multisport_data.py`
- `backend/app/ml/features/engineer_multisport_features.py`
- `backend/app/ml/features/sport_aware_features.py`
- `backend/app/ml/features/outcome_labels.py`
- `backend/app/ml/features/feature_timestamps.py`
- `backend/app/ml/features/kickoff_safe_features.py`

**Training and prediction**

- `backend/app/ml/training/train_multisport_baseline.py`
- `backend/app/ml/training/train_sport_aware_baseline.py`
- `backend/app/ml/predict_multisport.py`
- `backend/app/ml/predict_sport_aware.py`
- `backend/app/ml/probability_validation.py`

**Sprint 3 tests and fixtures**

- `backend/tests/test_sport_aware_features.py`
- `backend/tests/test_predict_sport_aware.py`
- `backend/tests/test_outcome_labels.py`
- `backend/tests/test_probability_validation.py`
- `backend/tests/test_feature_timestamps.py`
- `backend/tests/test_kickoff_safe_features.py`
- `backend/tests/fixtures/sprint3_match_outcomes.json`
- `backend/tests/test_sprint3_match_fixtures.py`

## 9. Local Testing

Run from the repository root with the Python virtual environment activated:

    python -m pytest backend/tests -v

Last verified complete backend suite before the sports-reference cleanup:

**159 passed, 0 failed, in 3.08 seconds.**

After the cleanup, individual verification results include:

- Outcome-label tests: 23 passed.
- Probability-validation tests: 19 passed.
- Match-fixture tests: 10 passed.

The complete backend regression suite must be rerun after all documentation and code changes are finalized.

## 10. Integration Limitations and Handoff

The sport-aware training and prediction components are implemented, but the complete production prediction API is not yet integrated.

The backend team still needs to confirm:

1. The mapping between backend `match_id` and ML `game_id`.
2. The final prediction request and response schema.
3. The feature-generation process for future matches.
4. How timestamp safeguards are enforced during backend inference.
5. Where trusted model artifacts are stored and loaded.
6. Whether the NFL/MLB/EPL implementation scope supersedes the original NBA/NFL/UEFA Jira requirements.

Synthetic fixtures validate expected behavior, while historical datasets support baseline model evaluation.

Model predictions should be presented as experimental probabilities, not guaranteed results.