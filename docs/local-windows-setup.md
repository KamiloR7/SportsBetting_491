Latest account/parlay update: see [Parlays and account pages](../backend/docs/parlays_and_account_pages.md) for current navigation, setup and verified balance. Earlier snapshots below are historical.

For the detailed ML evaluation and match-input breakdown, including the read-only audit setup command, see [ML evaluation dashboard](ml-evaluation-dashboard.md).

# Andrew local PostgreSQL demo

For the subsequent multi-season import, redesigned UI and historical replay, see [Expanded app handoff](sprint5-expanded-app.md). Its current data counts and model paths supersede the initial setup snapshot below.

Updated November 15, 2026. PostgreSQL 17.12 is running locally from the official EDB Windows binaries in build/postgres-runtime. It is a project process, not a Windows service. Docker was attempted but failed internally; Docker is not needed for this setup.

## Open the app

http://127.0.0.1:5173/dashboard

The browser is signed into a local demonstration account. It began with 1,000 virtual points and now has 900 after the verified 100-point Seattle bet on real match 66. That bet is pending; no result was fabricated. You can create your own account from the login screen. Use only demonstration passwords here.

## Verified on this computer

- Fresh PostgreSQL database sports_betting_demo, base schema and additive auth/betting setup completed.
- 167 genuine ESPN fixtures imported: NFL 58 completed, 7 in progress, 33 scheduled; MLB 8 completed and 1 postponed; EPL 40 completed and 20 scheduled. Snapshot timing is recorded in build/real-fixtures.json. Upcoming MLB is empty during this window.
- Separate models trained on this local database, stored under build/live-models. These are small-window models, particularly MLB with only eight results. Their accuracy is not the previously reported raw-dataset accuracy.
- Browser registration and session login succeeded. Wallet initialized to 1,000 points.
- Match 66 Raiders vs Seahawks automatically predicted not-home-win 56.793%; history 4/3 games. Browser bet accepted: 100 points on Seattle, demo odds 2.5000, potential total return 250, wallet 900, PENDING.
- Match 67 Cardinals vs Rams automatically predicted not-home-win 54.254%; history 4/4 games.
- Screenshots: build/real-match-bet-receipt.jpg and build/real-match-second-prediction.jpg.

## Start after a restart

Open PowerShell in this repository and run:

```powershell
.\Start-LocalApp.ps1
```

The script starts the existing saved PostgreSQL database, backend and frontend in hidden windows. It preserves processes already listening on the app ports. It does not recreate the schema or download data. Database credentials are in the ignored backend/.env; do not copy them into Git or chat. Saved database files are in ignored build/postgres-data; do not delete that folder or move it while PostgreSQL is running.

The script requires the same available python and node commands used for setup. Do not start two PostgreSQL processes on the same data directory. Backend logs are under build/backend-*.log and database logs are in build/postgres.log.

## Refresh genuine matches and settle finished bets

After reviewing the code changes, from backend:

```powershell
python -m app.database.refresh_real_matches --days-back 30 --days-ahead 14 --output ../build/real-fixtures.json --apply
```

This fetches actual provider results, preserves internal IDs and settles pending bets on final/cancelled matches. Odds remain synthetic demonstration prices. Re-running cannot pay the same bet twice. Changed completed results stop for manual payout review. This is an operator-triggered refresh, not an installed background scheduler.

Separate PostgreSQL integration tests: **137 passed, 9 skipped**, including settlement and concurrency coverage. This test run used its own disposable database, separate from the browser demo records.

## Review and limitations

No commits or pushes have been made. The source changes still need PR and peer review. The earlier handoff document describes the initial blocked setup; this file records the subsequent successful local setup. The raw-dataset evaluation remains separate from these small-window live models. The current UI remains binary for EPL prediction while betting supports home/draw/away. Local database import and two-match browser prediction checks have now run successfully; see build/postgresql-integration-tests.txt for the separate PostgreSQL payout/concurrency test results.
