# Sprint 5 betting and real data integration draft

**Subsequent update:** Local PostgreSQL is now running, 167 real fixtures were imported, two browser predictions and a virtual bet succeeded, and PostgreSQL integration tests finished with 137 passed and 9 skipped. See [current Windows setup](local-windows-setup.md). The initial preparation notes below are retained as history; their database-blocked status has been resolved.

Prepared November 15, 2026 for Andrew Vedder. This is an uncommitted working copy of GitHub main snapshot 834ec46, downloaded into the project workspace. The older Downloads checkout remains unchanged. The code is ready for peer review; PostgreSQL import and full browser betting remain unverified because localhost:5432 refused connections. No PR, commit, push, database migration, real-match write, or live payout was performed.

## What GitHub contains

PR 52 merged into the betting branch, then PR 51 merged that branch into main. Both guides are in this snapshot. Recent main also contains dashboard filters, browser prediction history, feed freshness checks and the earlier ML pipeline. The prior Downloads checkout is older (4015a7b). Read backend/docs/backend_integration_readiness.md for your teammate's exact database contract.

## Changes in this draft

- Registration and login now use backend sessions and the two-stage CSRF flow.
- Wallet balance, sign-out, owned betting history and balance refresh use the real APIs.
- Match details load database markets and allow an integer virtual-point stake with an exact decimal payout preview. Repeated network retries preserve the request key and payload.
- Predictions load automatically on match details and include a probability meter and manual retry. Sport-list prediction cards are not implemented.
- Default model directory resolves from repository root, fixing backend working-directory path confusion.
- Prediction history uses only prior UTC dates and the same league. Missing team history returns unavailable instead of predicting from zero statistics.
- A new ESPN refresh CLI downloads genuine matches and maintains provider mappings and internal match IDs. Its explicit apply mode creates synthetic-odds markets only for future scheduled matches and invokes existing settlement for completed/cancelled results. It refuses changed completed results; corrected payouts require manual review. No recurring scheduler is installed.
- UI prices are explicitly synthetic demo odds, including on genuine matches. No bookmaker feed, spreads or totals are implemented.

## Verified evidence

Frontend build and lint passed. Full backend tests: 484 passed, 140 skipped. Separate localhost HTTP flow: 1 passed, 1 PostgreSQL variant skipped. These include API tests with SQLite fixtures, not browser/PostgreSQL integration. Saved output: build/sprint5-test-results.txt. The new fixture adapter has three normalization tests; its PostgreSQL write path has not run.

Downloaded completed-match datasets: NFL 954, MLB 7,280, EPL 1,240. Source URLs, retrieval time and hashes are in data/raw/provenance.json. A separate ESPN schedule snapshot contains 167 events over the 30-days-back/14-days-ahead request window in build/real-fixtures.json. An empty sport window is legitimate, particularly during the MLB offseason.

| Sport | Train | Held out | Correct | Accuracy | Training-majority baseline |
|---|---:|---:|---:|---:|---:|
| NFL | 767 | 187 | 106 | 56.68% | 49.73% |
| MLB | 5,831 | 1,449 | 805 | 55.56% | 53.00% |
| EPL | 990 | 250 | 162 | 64.80% | 59.60% |

These results evaluate binary home win versus not-home-win. EPL draws are part of not-home-win. They do not establish a three-class EPL prediction model or profitability. Six features: both teams' cumulative win rates, average scores and average scores allowed. StandardScaler plus logistic regression, random state 42. Whole-date chronological split near 80/20; scaler and classifier fit on training only. Holdout features expand with results from earlier holdout dates, with weights fixed. No same-day results. The audit verifies scaler means against the training partition and perturbs target/later scores for the first and last holdout games of each sport. This is a targeted leakage audit, not proof of every provider timestamp.

Two repeatable NFL holdout examples: Pittsburgh vs Miami on 2025-12-15, home-win probability 53.2496%, predicted home win, actual home win; Seattle vs LA on 2025-12-18, 55.6369%, predicted home win, actual home win. These were direct saved-model runs, not a live PostgreSQL API dry run. Additional examples and split dates are in build/sprint5-holdout-audit.json.

## Exact local setup and remaining verification

Use the fresh-database instructions in backend/docs/backend_integration_readiness.md. PostgreSQL 17 and a configured authorized local account are prerequisites. Do not load the base SQL into an existing populated database. Do not copy teammate credentials. Configure backend/.env privately with the five DATABASE_* values. This workspace has no database configuration copied into it.

From repository root, after creating a fresh schema and running the guide's virtual-betting setup and base reference seed (omit seed-demo):

```powershell
$env:PYTHONPATH='backend'
python -m app.database.refresh_real_matches --days-back 90 --days-ahead 14 --output build/real-fixtures.json
```

Review the downloaded JSON first. The following is a database write and payout operation; run it only against the prepared local integration database after peer review. It fetches a new snapshot before applying, and existing incompatible mappings or corrected final results stop the run. Earlier successfully processed matches remain committed, and rerunning preserves mapped IDs.

```powershell
python -m app.database.refresh_real_matches --days-back 90 --days-ahead 14 --output build/real-fixtures.json --apply
```

This draft's database apply path needs PostgreSQL verification before relying on it. It creates missing exact-name/abbreviation team references, provider team mappings and season references. Ambiguous team/season resolution fails rather than guessing. A 90-day snapshot is partial history. For consistent live inputs and model training, train a separate set of models from the imported database history; do not report the raw-dataset accuracy table as accuracy of these newly trained artifacts.

From backend:

```powershell
python -m app.ml.train_local_match_models --output ../build/live-models
$env:MODEL_DIRECTORY=(Resolve-Path ../build/live-models).Path
$env:PREDICTION_MODEL_DIR=$env:MODEL_DIRECTORY
$env:LOCAL_DEMO_HTTP='true'
$env:VIRTUAL_BETTING_ENABLED='true'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Train into a fresh version directory each time. Multiple artifacts for one sport are deliberately rejected by the registry; do not select an arbitrary newest model. The training command requires completed matches and both outcome classes for all three leagues. Extend the real-data window if a sport lacks coverage. The raw-dataset models already generated in build/sprint2-models are a reproducible evaluated baseline, but their longer history differs from the partial ESPN database window.

In another terminal from repository root:

```powershell
npm --prefix frontend ci
npm --prefix frontend run dev -- --host 127.0.0.1
```

Open http://127.0.0.1:5173/login. Keep this exact hostname so the API proxy, cookies and backend origin checks agree. Create an account, verify 1,000 points, choose a sport and a future genuine match, open details, inspect its automatic prediction, select an open market and stake 100. At demo odds 2.5000, potential total return is 250 and balance becomes 900 after acceptance. A winning final result credits 250 (balance 1,150), a loss leaves 900 and void refunds 100. These balances are verified backend test expectations; browser/PostgreSQL confirmation is pending. For genuine matches wait for real results and rerun the refresh; do not fabricate final scores to demonstrate a payout.

## Practical presentation outline

1. Before presenting: verify database connection, current fixture snapshot, trained-model paths and open markets. Choose two genuine upcoming match IDs from GET /matches; IDs are environment specific. Avoid claiming MLB upcoming games if its season window is empty.
2. Open NFL or EPL, select match A. Show automatically loaded probabilities, history counts and market. Explain that predictions do not determine settlement.
3. Select an outcome and place a 100-point virtual bet. Show the accepted receipt, deducted balance and PENDING history. Repeat with match B if enough points remain.
4. Show a previously completed real bet and its settled status, or clearly label backend settlement test evidence if no real pending bet has finished yet. Refresh balance/history.
5. Show the held-out accuracy table, its sample counts and baseline comparison. Briefly explain prior-day inputs and fixed model weights. No live source code is needed.

Capture screenshots only after verifying real database/browser results: two prediction panels, accepted receipt plus wallet, settled history plus wallet. The older prediction-debug screenshot is synthetic historical evidence and must not be presented as this integration's live result.

## Repeatable evaluation and tests

From repository root:

```powershell
$env:PYTHONPATH='backend'
python -m app.ml.run_multisport_pipeline --raw data/raw --output build/sprint2-models
python -m app.ml.verify_sprint5_holdout
python -m pytest backend/tests -q -rs
npm --prefix frontend run build
npm --prefix frontend run lint
```

Keep the source data snapshot and generated report together. Data refresh changes evaluation inputs. Saved raw source files are local-only; do not include them in the PR. The review patch is build/sprint5-integration.patch. Do not merge it until PostgreSQL apply tests and browser integration have passed.

## Remaining issues

- PostgreSQL unavailable locally, so full import, mapping reconciliation, persistence, concurrency and payout verification remain pending.
- The default prediction service remains binary for EPL; three-way odds do not imply three-way ML.
- The refreshed live database may have less history than the evaluated raw snapshots.
- Dependency audit reports five findings (three moderate, two high), including Vite and zod. See build/frontend-audit.json; dependency updates need their own verification.
- No successful live integration screenshots were captured. Existing evidence is test output, provider snapshots, saved model metadata and holdout predictions.
