# Vigor — Sprint 3 Machine Learning Contract

## Overview

This document describes the proposed Machine Learning input/output interface for NBA, NFL, and UEFA match predictions.

**Status:** Proposed contract; backend integration and teammate confirmation pending.

## 1. Supported Prediction Outcomes

| Sport | Outcomes |
|---|---|
| NBA | `home_win`, `away_win` |
| NFL | `home_win`, `away_win` |
| UEFA | `home_win`, `draw`, `away_win` |

All outcome probabilities must be finite numbers between 0 and 1 and must sum to 1 within a tolerance of `1e-6`.

## 2. Model Input Contract

| Field | Type | Requirement |
|---|---|---|
| `match_id` | String or agreed backend ID | Required; unique match identifier |
| `sport` | String | Required; NBA, NFL, or UEFA |
| `start_time` | ISO 8601 datetime | Required; timezone-aware kickoff time |
| `feature_as_of` | ISO 8601 datetime | Required; must precede kickoff |
| `home_team` | String | Required |
| `away_team` | String | Required |
| `home_win_rate` | Number | Historical win rate, 0–1 |
| `away_win_rate` | Number | Historical win rate, 0–1 |
| `home_avg_score` | Number | Nonnegative historical average |
| `away_avg_score` | Number | Nonnegative historical average |
| `home_avg_allowed` | Number | Nonnegative historical average |
| `away_avg_allowed` | Number | Nonnegative historical average |

Historical results must have been available by `feature_as_of`.

## 3. Prediction Response Example

```json
{
  "match_id": "UEFA-001",
  "sport": "UEFA",
  "predicted_outcome": "home_win",
  "probabilities": {
    "home_win": 0.50,
    "draw": 0.30,
    "away_win": 0.20
  },
  "model_version": "uefa-v1"
}
```

The `predicted_outcome` must correspond to an outcome with the maximum probability.

## 4. Missing and Invalid Data Policy

- Missing `match_id`, sport, teams, or kickoff time: reject input.
- Missing or invalid predictive features: reject input until a documented imputation policy is agreed.
- Features at or after kickoff: reject input.
- Historical results unavailable at prediction time: reject input.
- Missing scores for final matches: reject input.
- Scheduled, live, postponed, or cancelled matches: exclude from completed-match training labels.
- Final NFL ties: exclude from binary winner training labels.
- Final UEFA draws: retain as the `draw` class.

## 5. Relevant Source Files

- `backend/app/ml/features/outcome_labels.py` — Sport-specific outcome labels.
- `backend/app/ml/features/feature_timestamps.py` — Timestamp cutoff validation.
- `backend/app/ml/probability_validation.py` — Prediction probability validation.
- `backend/tests/fixtures/sprint3_match_outcomes.json` — Synthetic match fixtures.
- `backend/tests/test_sprint3_match_fixtures.py` — Fixture validation tests.
- `backend/tests/test_outcome_labels.py` — Outcome-label unit tests.
- `backend/tests/test_feature_timestamps.py` — Timestamp validation tests.

## 6. Local Testing

Run from the repository root with the Python virtual environment activated:

```bash
python -m pytest backend/tests -v
```

Latest verified local result: **141 passed, 0 failed**.

## 7. Integration Limitations and Handoff

The existing training pipeline supports NFL, MLB, and EPL with binary home-win versus not-home-win outcomes. It does not yet implement NBA classification or UEFA three-way inference.

The new labeling, timestamp, and probability-validation utilities are currently standalone components. Integration into model training, inference, and the backend prediction API requires coordination with the responsible teammates.

The backend team should confirm the match identifier format, timestamp serialization, prediction response schema, and model-loading interface before integration.