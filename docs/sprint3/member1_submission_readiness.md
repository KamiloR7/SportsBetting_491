# Member 1 Sprint 3 Submission Readiness

Assessment date: 2026-10-15

## Ready on the feature branch

- Multi-sport model loading and deployment validation
- Prediction service and `POST /predictions`
- NFL MLB and EPL selection paths
- Prior-match team history lookup
- Request validation and controlled errors
- Standard response with probabilities confidence model version and history counts
- Backend API and service tests
- Backend API documentation
- Frontend prediction request and result display
- CI configuration for Python tests frontend lint and frontend build
- Final test plan document prepared for Google Docs import
- Manual-test and work-evidence workbook prepared for Google Sheets import
- Eight live Jira issues created, assigned, added to Sprint 3, and moved to In Review

Local verification on 2026-10-15:

```text
136 Python tests passed
Frontend lint passed
Frontend production build passed
```

## Existing Sprint 3 evidence

Git history contains Member 1 commit `9a806cc` on 2026-10-08 for ML regression tests and CI coverage. It was merged through PR 21 by teammate Andrew Vedder as merge commit `02cb42a`.

The new backend work is in commits `3d392ce` and `3a47b96` on branch `aymoon13/sprint3-model-loading`. The branch is intentionally being held for one combined pull request during class.

## Still required before submission

1. Push the latest commits and open one combined pull request to `main` during class.
2. Confirm both hosted CI jobs pass on that pull request.
3. Ask another group member to review and approve the pull request.
4. Merge only after approval and successful CI.
5. Complete the eight manual cases in the evidence workbook with actual results and links or screenshots.
6. Import the test plan to Google Docs and the evidence workbook to Google Sheets, then add shareable links.
7. Attach the combined PR, hosted CI result, and final evidence links to Jira issues SCRUM-261 through SCRUM-268.
8. Add the final repository, PR, CI, Jira, test plan, evidence, and Sprint 3 ChatGPT links to the submission document.
9. Continue real Sprint 3 work on at least three additional dates if the goal is the rubric's five-day evidence tier. Do not backdate commits or invent activity.

## Important limitation

The Sprint 2 EPL model is binary. `NOT_HOME_WIN` includes draws and away wins. The API and frontend disclose that limitation and do not claim to provide separate draw and away-win probabilities.
