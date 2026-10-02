# Sprint 2 review evidence — October 1, 2026

## Scope

Recovered the local multi-sport dataset validator, prior-game features,
chronological split, logistic regression trainer, evaluation helpers and tests.
Existing main-branch NFL code and teammates' authentication/data-ingestion work
are preserved. This change is an initial implementation, not completion of all
Sprint 2 real-data training requirements.

Related individual work:
- [SCRUM-129](https://cpsc-491-group5.atlassian.net/browse/SCRUM-129)
- [SCRUM-130](https://cpsc-491-group5.atlassian.net/browse/SCRUM-130)
- [SCRUM-131](https://cpsc-491-group5.atlassian.net/browse/SCRUM-131)
- [SCRUM-132](https://cpsc-491-group5.atlassian.net/browse/SCRUM-132)

## Local verification

On Python 3.12.14, in a clean virtual environment, install the editable project,
`backend/requirements.txt`, and pytest, then run from the repository root:

```sh
PYTHONPATH=backend python -m pytest -q
python -m compileall -q backend src tests
git diff --check
```

Result: **75 tests passed**. Compilation and whitespace checks passed.
Tests use synthetic fixtures and mocks; no live API, production database,
deployment or real-data model performance is verified by this result.

## CI changes

Preserve the existing pull-request/main-push triggers and Python 3.12 job.
Install the project and scikit-learn, expose the backend import path, publish
JUnit test results even when tests fail, and restrict workflow token permissions
to read-only. Include run attempt in build IDs so a rerun can be distinguished
from the original run. The complete test suite includes the new ML tests.
GitHub-hosted execution must be checked separately after opening the PR.

## Review and remaining work

Review before merging to main. Confirm dataset source provenance and adapt real
NFL/MLB/EPL records to the input contract before reporting performance. This
baseline predicts home win versus not-home-win; EPL draws are not away wins.
Follow-up work includes robust date/score validation, timestamp-group split
boundaries and tiny-dataset rejection, probability calibration evaluation,
dataset/model-content fingerprints and immutable model artifacts.

Frontend build/deployment, dependency locking, branch protection and evidence
of every member's contribution are not established by this PR. Each member
maintains their own tickets and contribution evidence.
