Latest account/parlay update: see [Parlays and account pages](../backend/docs/parlays_and_account_pages.md) for current navigation, setup and verified balance. Earlier snapshots below are historical.

# Expanded Vigor app handoff

**Latest pricing update:** Future markets now use trained model odds, with a three-way EPL classifier and a 5% target pricing margin. See [Model priced betting](../backend/docs/model_priced_odds.md). The initial binary/live-price status below is retained as implementation history. The demo wallet is now 800 after a second 100-point model-priced test bet; the earlier accepted bet is preserved.

Prepared November 15, 2026. The local app now uses a larger PostgreSQL history and a redesigned dashboard, sign-in page, match center and wallet. Code changes are uncommitted and still require PR and peer review.

## Open and sign in

App: http://127.0.0.1:5173/dashboard

Use the existing local demo account, or create another account from Sign in. Demo credentials were supplied in the chat; database credentials remain only in ignored backend/.env. Your existing 900-point wallet and pending Seattle bet were preserved.

From this repository, run .\Start-LocalApp.ps1 after restarting your computer. It starts the saved project-local PostgreSQL cluster and the frontend/backend. It now points to build/live-models-expanded. Do not delete build/postgres-data: that is the persistent local database, not a disposable build output.

## What changed

- New dark Vigor design with lime accents, readable match cards, proper sign-in/register tabs, password visibility control, working entry route, and no missing logo image or forced splash delay.
- Automatic forecast previews on the first six upcoming cards, automatic match forecasts, probability meters and clear estimate labels.
- Search teams across the database and browse 30 matches per page. Completed results are newest first.
- MLB empty-upcoming state links directly to completed games.
- Wallet activity, clearer bet status/returns, virtual demo-point refill and balance refresh every 30 seconds.
- Match center places forecasts and betting above recent form. Historical context excludes the selected UTC day and later results.
- Historical replay trains a fresh logistic model only on completed games from earlier UTC dates, excluding the target result. It displays the actual result and whether the forecast matched. Earliest matches without 30 prior league games or prior history for both teams show an explanation.
- Existing /predictions rejects a model whose training end reaches the target date, preventing a later-trained model from being represented as an earlier forecast.
- Public access policies explicitly cover the replay and aggregate evaluation endpoints.
- Compatible frontend dependency updates resolved the five previously reported findings. Final npm audit: zero known vulnerabilities; frontend build and lint pass.

## Data and repeatability

The database contains 9,551 matches: 7,288 completed MLB, 954 completed NFL, 1,248 completed EPL, 53 scheduled, seven in progress and one postponed. Results come from saved nflverse, MLB Stats API and football-data.co.uk source snapshots plus the existing ESPN fixture snapshot. Source bytes and normalized dataset hashes are checked before historical import.

9,474 historical provider records were imported. A complete repeat of the import left match count at 9,551, with existing wallets and bets unchanged. See build/history-repeatability.json. Provider match IDs are mapped to internal IDs; ambiguous/conflicting records stop. MLB doubleheaders require exact kickoff matching rather than broad same-day deduplication. Source mappings and season/team memberships are retained. Raw data and model binaries stay local and must not be included in the code PR.

From backend, the repeatable import command is:

```powershell
python -m app.database.import_real_history
```

This imports the previously downloaded and hash-verified snapshot in data/raw. To obtain a new history snapshot first, from repository root:

```powershell
$env:PYTHONPATH='backend'
python -m app.ml.features.download_multisport_data --output data/raw
```

To fetch future/current fixtures and apply actual completed results/settlement, from backend:

```powershell
python -m app.database.refresh_real_matches --days-back 30 --days-ahead 14 --output ../build/real-fixtures.json --apply
```

Refresh is an explicit operator action, not an installed scheduler. It preserves existing markets and prices, rejects conflicting completed results and calls the existing idempotent settlement service. No fabricated final scores were applied to genuine matches. Betting odds are still explicitly synthetic demonstration prices, including on genuine fixtures.

## Verified browser scenarios

1. Sign out, open the redesigned sign-in page and log in with the existing demo account. Wallet returns as 900 points, with the original bet preserved.
2. NFL upcoming: the first six cards load forecast previews. Open a match for its complete forecast and virtual market.
3. MLB upcoming: an honest empty state links to completed games. Completed MLB browsing now has thousands of results, pagination and team search.
4. Open http://127.0.0.1:5173/matches/100?league=baseball&status=final. Cleveland vs Tampa Bay now replays successfully. It trains on 7,280 earlier games through September 27, 2026, estimates Cleveland at 54.1768%, and marks the forecast as a miss against the actual 3–7 result. Team histories contain 484 and 486 earlier games.
5. Current balance and saved bet remain unchanged by replay or data import. Replay does not place a bet, settle a result, or claim the prediction was recorded before the game.

Screenshots: build/redesigned-sign-in.jpg, build/redesigned-dashboard.jpg, build/redesigned-mlb-board.jpg and build/expanded-mlb-replay.jpg.

## Checks and evidence

- Full backend suite with the isolated Sprint 5 PostgreSQL test database enabled: 560 passed, 66 skipped. Output: build/expanded-postgres-tests.txt. Other separately guarded PostgreSQL suites were not configured; default HTTP-mode checks are run separately.
- Final replay/access-policy/match checks: 13 passed, including target/future-score perturbation, training-only scaler checks, insufficient history and invalid-target handling.
- Frontend production build and lint passed after dependency updates. Audit output: build/frontend-audit-final.json.
- Repeated historical import: identical match count, wallet balances and bet states.

The dashboard evaluation panel intentionally shows the saved raw-dataset baseline, not accuracy of every newly rebuilt replay or the expanded database model. Existing baseline held-out results remain NFL 56.68% (187 games), MLB 55.56% (1,449), EPL 64.80% (250), with corresponding majority baselines shown beside them. All targets remain binary home win vs not-home-win; EPL draws belong to not-home-win. A true three-class EPL model and a bookmaker odds feed are not included.

## Practical demo

Open NFL to show automatic forecasts; open a future match to show its market and place virtual points. Open your wallet for bet status and signed transaction history. Then use Baseball → Final → a recent completed game to show historical replay and its honest actual-result comparison. Finish with Model insights to explain held-out sample counts and baseline comparison. Keep source code closed during the demo.

Review package: build/sprint5-integration.patch and build/changed-files.json. Database files, private settings, raw source downloads and generated models are excluded. Nothing has been committed or pushed.
