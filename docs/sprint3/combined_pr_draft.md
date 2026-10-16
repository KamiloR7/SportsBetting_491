# Combined Sprint 3 Pull Request Draft

Suggested title:

```text
Sprint 3 Member 1 prediction API and evidence
```

Suggested description:

```markdown
## Summary

Completes the Member 1 Sprint 3 Backend and Database workflow for NFL, MLB, and EPL predictions. This PR connects the trusted Sprint 2 model artifacts to a validated FastAPI prediction endpoint, stored match history, and the frontend match-details flow.

## Jira

- [SCRUM-261](https://cpsc-491-group5.atlassian.net/browse/SCRUM-261) model loading
- [SCRUM-266](https://cpsc-491-group5.atlassian.net/browse/SCRUM-266) prediction service and endpoint
- [SCRUM-262](https://cpsc-491-group5.atlassian.net/browse/SCRUM-262) team and history lookup
- [SCRUM-263](https://cpsc-491-group5.atlassian.net/browse/SCRUM-263) validation and error handling
- [SCRUM-268](https://cpsc-491-group5.atlassian.net/browse/SCRUM-268) response and probability contract
- [SCRUM-267](https://cpsc-491-group5.atlassian.net/browse/SCRUM-267) backend integration tests and CI
- [SCRUM-264](https://cpsc-491-group5.atlassian.net/browse/SCRUM-264) API documentation and frontend integration
- [SCRUM-265](https://cpsc-491-group5.atlassian.net/browse/SCRUM-265) submission artifacts and evidence

## Changes

- Added a multi-sport model registry with checksum and metadata validation.
- Added cached NFL, MLB, and EPL artifact loading with controlled deployment errors.
- Added `POST /predictions` with strict request and response schemas.
- Added prior-match team-history lookup and leakage-safe feature construction.
- Added a standardized binary outcome, probability, confidence, model-version, and history response.
- Added controlled 404, 422, and 503 behavior.
- Added backend service and API integration tests.
- Connected the match-details page to the prediction endpoint.
- Added frontend lint and production build to CI.
- Added API documentation, final test plan, manual-test workbook, Jira alignment, and submission-readiness evidence.

## Local verification

- [x] 136 Python tests passed
- [x] Frontend lint passed
- [x] Frontend production build passed
- [x] DOCX rendered and visually inspected
- [x] DOCX accessibility audit reported no findings
- [x] XLSX formulas and key ranges inspected
- [x] XLSX previews visually inspected

## Known limitation

The Sprint 2 EPL artifact is binary. `NOT_HOME_WIN` includes a draw or away win. This PR documents that limitation and does not expose unsupported three-class probabilities.

## Review requested

Please verify the model deployment safeguards, prior-game history query, response/error contract, frontend flow, automated tests, and evidence documents. Do not merge until both CI jobs pass and a teammate approves this PR.
```

Before opening the pull request:

1. Push all local commits on the feature branch.
2. Open the pull request against `main`.
3. Request a teammate review.
4. Confirm both CI jobs pass.
5. Add the PR and CI links to the Jira issues and submission evidence.
6. Merge only after approval.
