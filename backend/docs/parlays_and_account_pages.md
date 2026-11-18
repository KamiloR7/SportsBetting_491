# Parlays and account pages

Local implementation verified November 15, 2026. Virtual points only. Uncommitted; PR and peer review required.

## Setup

The existing localhost installation is already configured. Start from the repository with `./Start-LocalApp.ps1`. On another machine, first complete the existing database/auth/betting setup and [model pricing setup](model_priced_odds.md), import real fixtures/results, and train models. PostgreSQL must be installed or supplied locally; the saved database is not source code and is not included in a Git submission.

Back up the authorized local database before additive setup. From `backend`:

```powershell
python -m app.database.setup_parlays
```

This adds `virtual_parlays` and `virtual_parlay_legs`; existing wallets and bets are preserved. Review SQL in `parlay_schema.sql`. In ignored `backend/.env`, enable `VIRTUAL_BETTING_ENABLED=true`, `MODEL_ODDS_ENABLED=true`, and `PARLAYS_ENABLED=true`, then restart the backend. `LOCAL_DEMO_HTTP=true` is only for a loopback HTTP demonstration.

## Practical demo (no live code presentation)

1. Open http://127.0.0.1:5173/insights. Explain real completed results, the six prior-day inputs, scaling and logistic regression. Contrast an individual probability with chronological held-out accuracy. At the illustrative 72% slider setting, fair odds are 1.39, offered odds 1.32 and a winning 100-point stake returns 132. This is explicitly an illustration.
2. Sign in through the local Sign in page. Open Wallet activity. Type 137 and click Add points. The balance rises by exactly 137 and the ledger gets one matching credit. The button never automatically adds 1,000; new registration still starts at 1,000.
3. Open a future match, choose an outcome, and click Add to parlay. Repeat on a different game. Open Parlay builder, review both selections, stake and combined return, then click Place parlay. Adding selections alone does not debit points.
4. Open Active bets to see the ticket and each leg. Open Bet history for settled tickets; an empty state is expected before real results are settled. Wallet activity shows the stake debit.

Verified live example: Manchester City–Fulham match 148, home at 1.47, plus Baltimore Ravens–LA Chargers match 70, home at 1.47. Stake 50, combined 2.1609, potential total return 108, accepted parlay #1 PENDING. Wallet moved 1,600 → 1,737 after the custom refill → 1,687 after the parlay. Existing four single bets were preserved. No final result was fabricated. These games are time-sensitive: use two future model-priced matches when repeating later; prices and IDs can differ on another database.

Evidence in ignored `build`: `model-insights-explained.jpg`, `wallet-custom-refill.jpg`, `parlay-accepted.jpg`, `active-bets-tabs.jpg`, `parlay-full-tests.txt`.

## Contract and limits

- POST /parlays accepts a request_key, integer stake 1–1,000,000 and 2–8 legs with match_id, outcome_id and expected_odds. GET /parlays and GET /parlays/{id} return only the current user's tickets. CSRF protects placement.
- Distinct future games only; one selection per game. Prices are checked again before debit. A stale price returns 409 and requires review. Each accepted leg stores its odds and quote reference.
- Combined decimal odds multiply accepted leg odds. Total return floors stake times product to whole points; storage uses eight decimal places for the combined product. Maximum return is 2 billion points. Margins compound. Independence is assumed; there is no joint probability model or same-game parlay engine.
- Any losing leg loses the ticket. Voids count as 1.00; all voids refund the original stake. Otherwise every non-void leg must win. Actual results, never a model forecast, settle the ticket. Later leg results remain tracked after an early loss.
- Sorted row locks and unique request keys protect concurrent placement/settlement. Identical retries return the original ticket; changed payloads under an existing key return 409. Accepted prices survive later repricing.
- POST /wallet/demo-topup accepts amount 1–1,000,000 and request_key. Identical retry credits once; changing the amount under the same key conflicts. The omitted-amount API default remains 1,000 for legacy clients; the new UI always sends the typed amount.
- The real-result refresh command in the model-pricing guide triggers settlement. No automatic background refresh is installed.

## Validation

Full backend run: 627 passed, 68 skipped, 301 warnings. Sprint 5 betting/model/parlay PostgreSQL variants used a separate disposable local test database; SQLite-only row-lock cases and unrelated opt-in suites account for skips. Parlay checks cover win, loss, one void, all void, EPL draw, stale prices, ownership, session denials, CSRF, locked prices, duplicate requests and concurrent settlement/placement. Fake test scores/models are isolated from browser demo records. Frontend production build and lint passed.

Model limitations: simple team-history features, no injury/lineup/weather inputs, no demonstrated probability calibration or betting profitability. Historical replay is reconstructed and separate from three-way EPL pricing. Local HTTP and unrestricted demo-point refill are demonstration settings.
