Current review update: a separate Git checkout and feature branch have now been prepared for the requested PR. The original local app and saved database remain in their original workspace. The workflow notes below describe the preparation snapshot.

# Andrew Vedder — local Sprint 5 contribution draft

Prepared for review, November 15, 2026. This is a description of the local changes, not a statement that they are merged or that course credit is guaranteed.

## Attribution and scope

The teammate's merged backend/database PRs #51 and #52 supplied registration, sessions, wallets, single-bet placement/settlement and the integration foundation. Preserve that attribution. Andrew's local integration work extends that foundation with real multi-season data, verified ML forecasts and held-out evaluation, model-derived odds with immutable quote evidence, historical replay, a redesigned frontend, explanatory Model Insights, parlays, separate account pages and custom point refill amounts. Review each diff and adapt this description to the work you can explain and your course's assistance-disclosure requirements.

## Evidence to present

- Model: six cumulative prior-day team inputs; StandardScaler plus logistic regression; chronological evaluation before deployment refit. NFL 56.45%/186 tests, MLB 55.49%/1,458, EPL three-way 44.98%/249. See backend/docs/model_priced_odds.md for baselines and limitations.
- Browser: forecasts on real fixtures, prior-only completed-match replay, model-priced accepted bet, custom 137-point refill and accepted two-leg parlay at 2.1609 with 50 stake and 108 potential return.
- Regression: latest full backend run 627 passed, 68 skipped; frontend build and lint pass. Screenshots and logs are retained locally in build.
- Payout correctness is demonstrated in isolated tests. Genuine pending games are not assigned fabricated outcomes for a demo.

## GitHub submission workflow

This working folder is a downloaded repository snapshot, not a Git checkout. No commit, push or PR has been made. `build/sprint5-integration.patch` and `build/changed-files.json` collect the cumulative source changes against downloaded main snapshot 834ec46. Review the list before applying it to a fresh clone; current main may have advanced.

1. Clone the group repository into a separate working folder and create a feature branch under your own Git identity.
2. Review/apply the patch to the matching baseline, or reconcile it against current main. `git apply --check <absolute-path-to-patch>` checks applicability; `git apply <absolute-path-to-patch>` applies after review.
3. Review `git diff` and the staged file list. Include source, tests, `.env.example` and documentation. Exclude `.env`, credentials, database files/backups, models, downloaded datasets, runtime binaries, node_modules and generated build files. Copy only selected sanitized screenshot evidence if desired.
4. Run backend checks and frontend build/lint in the clone with your own local setup. Read the schema/model setup guides; Git alone does not transfer the running PostgreSQL database.
5. Commit under your account, push your feature branch and open a draft PR describing the final changes, teammate attribution, tests and limits. Obtain code/schema review before merging.

Do not copy or replace the existing saved PostgreSQL data directory while it is running. Preserve the current local workspace until the reviewed clone works. Assistance used in preparation should be disclosed according to the instructor's policy.
