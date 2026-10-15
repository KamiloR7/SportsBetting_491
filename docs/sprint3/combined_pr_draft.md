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

- Add the actual Jira issue links for model loading, prediction service, history lookup, validation, testing, frontend integration, and documentation.

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
2. Replace the Jira placeholder with the real issue links.
3. Open the pull request against `main`.
4. Request a teammate review.
5. Confirm both CI jobs pass.
6. Merge only after approval.
