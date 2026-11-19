# ML evaluation dashboard and matchup inputs

Implemented on `andrew/ml-evaluation-dashboard`. This feature does not replace deployment models, import data, refill wallets or place bets.

## Review in the running app

1. Open http://127.0.0.1:5173/insights#ml-evaluation (or Model insights in the navigation).
2. Switch NFL / MLB / EPL. Compare held-out accuracy against the majority outcome selected from the training partition. Check train/test date ranges and the deployed snapshot identifier.
3. Read the confusion matrix: rows are actual results, columns are model picks. Counts and row percentages are shown. EPL includes Draw; this snapshot never selected Draw as its leading holdout pick, explicitly flagged on screen.
4. Compare leading-outcome confidence with actual correctness in 10-percentage-point bands. Empty bins are hidden; samples smaller than 30 are flagged. This is descriptive top-label calibration, not a calibration guarantee or a per-class reliability plot. Log loss scores the complete probability distribution. The weighted gap is descriptive expected calibration error for these bins.
5. Expand the leakage explanation. Earlier held-out results can update the historical features for later test games, while the fitted scaler/classifier stay fixed.
6. Open http://127.0.0.1:5173/matches/71?league=football&status=matchday and find **What went into this matchup?**. The comparison shows three statistics per team (six actual model inputs), prior-game counts and the UTC cutoff. Counts are context, not extra inputs. The evaluation link returns to the report.
7. A historical match such as `/matches/100?league=baseball` shows when the configured market model was trained after the target cutoff. Displaying its historical inputs does not make that later model eligible for forecasting the old game. Historical replay remains separately trained and labeled.

## Reproduce evidence

After the real-data import and `python -m app.ml.train_market_models` setup, run from **backend**, using the same environment and local database as the app:

```powershell
python -m app.ml.evaluation.market_audit
```

The command reads completed games only and reconstructs the original snapshot cutoff from the configured market-model manifest. It verifies the full feature/target dataset SHA-256 against the model metadata, fits the existing StandardScaler + LogisticRegression recipe on whole-date chronological training data, and checks the test/train counts, accuracy and log loss against the saved manifest. It writes aggregate evidence to the ignored `build/market-models/evaluation.json` under the configured model directory. It does not overwrite a pickle, retrain the deployed model, change a quote or write to the database.

If source results changed or an artifact is missing, that sport is explicitly unavailable. It does not silently substitute a newly trained dataset or fabricated matrix. The API binds the report to the current manifest hash and returns a controlled 503 for missing, malformed or stale reports. Regenerate and review the report after deliberate model changes. Live fixture polling does not change these saved evaluation metrics.

The deployment version identifies the fully refitted model snapshot. The holdout metrics come from a separate training-only fit, before that refit, not a claim that the deployed full-history model was evaluated on its own training rows. Models exclude same-day/target/future scores in each feature row. NFL/MLB ties are excluded from the winner labels; EPL draws are a class. Initial feature rows without history use zeros, as in the existing pipeline. The split is one approximately 80/20 chronological holdout, not cross-validation.

## Verified snapshot

Snapshot generated November 15, 2026. All three dataset fingerprints and original metrics reproduced exactly.

| Sport | Correct / held-out games | Training-majority baseline | Binned weighted confidence gap |
|---|---|---|---|
| NFL | 105/186 (56.45%) | 49.46% | 2.78 pp |
| MLB | 809/1458 (55.49%) | 52.95% | 1.32 pp |
| EPL | 112/249 (44.98%) | 41.37% | 5.22 pp |

These are held-out match-winner classifications, not personal betting win rates, profit claims or guarantees. EPL's three-way task differs from the two-way NFL/MLB task. No injuries, lineups, rest, weather or player props are inputs.

## API and UI implementation

- `GET /insights/audit`: read-only aggregate report; serves no account data, artifact paths or individual evaluation rows. No training runs in an HTTP request.
- `GET /insights/matches/{match_id}/inputs`: read-only current-database reconstruction through the same MatchHistoryRepository used by pregame inference. It applies strict start_time < target UTC midnight, requires prior history for both teams, and shows model eligibility separately.
- Input values are reconstructed now, not a stored pregame snapshot. Later provider corrections can alter old feature values. This is an input comparison, not a causal feature-importance explanation or a promise that the model favors the team with the largest individual statistic.
- The existing dashboard headline metrics and all betting/settlement behavior remain unchanged.

## Validation

61 focused tests passed: metric orientation/bin boundaries including 100% confidence; invalid distributions; mismatched dataset rejection; stale/missing audit API failure; target/same-day/future score perturbation; historical model eligibility; read-only endpoint behavior; existing prediction service, chronological dataset, sport-aware features and route policy inventory.

Frontend production build and lint passed. Browser checks verified NFL/MLB/EPL tab values, the EPL draw limitation, reliability bins, match input values (Texans 58.3% wins / 23.10 scored / 20.65 allowed versus Colts 45.9% / 23.72 / 25.00, from 60/61 earlier games), historical-model warning and the match-to-evaluation link. Observed values describe this local database snapshot.

Evidence in `docs/evidence/`: `ml-evaluation-nfl.jpg`, `ml-evaluation-mlb.jpg`, `ml-epl-confusion.jpg`, `ml-epl-reliability.jpg`, `ml-match-inputs.jpg`.
