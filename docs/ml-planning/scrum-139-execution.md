# SCRUM-139 Release Readiness and Data Source Review

**Review date:** 2026-11-19  
**Reviewer/execution:** Codex-assisted review for Ayman Sadek; no independent teammate sign-off is claimed.  
**Reviewed artifact:** `sprint2_real_data_results.json`, generated for source commit `9e1e1f781d2f2de9bf7ddf3adfd47e52eca897cf`.  
**Disposition:** Partial evidence. This records an actual review of the checked-in evidence and names the checks that still need a human or fresh CI run.

## Data source and exclusions review

| Sport | Source and recorded digest | Source rows | Selected rows | Recorded exclusions | Review outcome |
| --- | --- | ---: | ---: | --- | --- |
| NFL | [nflverse games.csv](https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv), `4fefc0180964799fafd2e9c0bba16ed2b1aad4cde8ecbf6e4423a0d6cc0b8b72` | 7,548 | 544 | Incomplete: 0 | Provenance fields and selection count present; raw snapshot unavailable for independent recount. |
| MLB | [MLB Stats API 2024 regular season schedule](https://statsapi.mlb.com/api/v1/schedule?sportId=1&season=2024&gameType=R), `9733d248b6a6d1635eb91802f504d70ebedc49b5aa87e7ae962cafb40b18879b` | 2,469 | 2,426 | Not completed regular season: 37; resumed-game leakage guard: 6 | Counts reconcile to selected rows; raw snapshot unavailable for independent recount. |
| EPL | [football-data 2023/24 E0](https://www.football-data.co.uk/mmz4281/2324/E0.csv), `b2e057b0ed959f198b0f63d2391c01239f3608e6de5db68edab3f88e04d07ff3`; [2024/25 E0](https://www.football-data.co.uk/mmz4281/2425/E0.csv), `d0c8ce4a96d886cf60cf101f570f4a3893844226f91c7bd769eb568c49edbfa4` | 380 + 380 | 760 | Incomplete/other division: 0 + 0 | Provenance fields and row counts present; raw snapshots unavailable for independent recount. |

The source report records date ranges and dataset hashes. The raw files are not
checked into this checkout (`data/raw/` contains only `.gitkeep`), so this
review did not redownload data, independently recompute source hashes, or
verify provider-side changes. No raw data was added to Git.

## Model and claim review

- Evaluation protocol is a fixed model with a chronological holdout and
  expanding prior-day observed results; it states there was no same-day result
  leakage or holdout-based tuning.
- The output is binary home-win versus not-home-win. The recorded evaluation
  identifies 175 EPL draws as not-home-win; this is not a three-way soccer
  outcome model.
- Under the SCRUM-138 comparison policy, the recorded NFL, MLB, and EPL results
  improve both Brier score and log loss over their training-prevalence
  baselines. The metric values and comparison are in
  [PR #60](https://github.com/KamiloR7/SportsBetting_491/pull/60).
- These offline holdout metrics do not guarantee future performance or betting
  profit. This review makes no profitability claim.

## Validation evidence

- Full repository regression pass recorded in
  [PR #57](https://github.com/KamiloR7/SportsBetting_491/pull/57): 361 passed,
  82% coverage for `backend/app/ml`, compile check passed, wheel build passed.
  This is a local run; no hosted CI result is claimed here.
- SCRUM-138 evaluator checks: 25 passed across
  `test_evaluate_multisport_models.py` and `test_ml_testing_backlog.py`.
- Fresh hosted CI status and a teammate review are pending on the separate
  ticket PRs. No live data-provider or deployed-service test was performed.
- This review is linked to the SCRUM-139 PR; attach its PR/CI links to Jira
  during the sprint evidence review.

## Remaining release checks

1. A teammate independently reviews the source selection and exclusion counts
   against the raw provider snapshots and records the reviewer/date.
2. Attach a fresh passing hosted CI run and confirm the uploaded test, coverage,
   and build artifacts.
3. Run a manual end-to-end review against the selected release candidate and
   add screenshots or video with timestamps if required by the sprint rubric.
4. Confirm the final PR review and any outstanding fixes before calling this
   checklist complete.
