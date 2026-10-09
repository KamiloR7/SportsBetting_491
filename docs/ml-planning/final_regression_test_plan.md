# Final ML Regression Test Plan

Related Jira: SCRUM-141.

This plan defines the final validation pass for Ayman Sadek's ML and CI testing
work before the semester submission.

## Scope

The final pass covers the ML data pipeline, prediction-model contract, model
evaluation outputs, and CI evidence. It does not claim ownership of teammate
frontend, authentication, deployment, or database tests.

## Commands

Run from the repository root.

```sh
python3.12 -m venv .venv-final
source .venv-final/bin/activate
python -m pip install --upgrade pip
python -m pip install -c backend/requirements-sprint2-tested.txt -r backend/requirements.txt pytest pytest-cov
python -m pip install -e .
PYTHONPATH=backend python -m pytest backend/tests tests --cov=backend/app/ml --cov-report=term-missing --cov-report=xml:build/coverage.xml --junitxml=build/test-results.xml
python -m compileall -q backend src tests
python -m pip wheel --no-deps . --wheel-dir build/dist
```

## Required evidence

- Jira links: SCRUM-135 through SCRUM-141.
- Pull request link for the final testing work.
- GitHub Actions run URL.
- Build identifier and commit SHA.
- JUnit test artifact or equivalent test log.
- Coverage artifact if generated.
- Screenshots or copied output for any manual checklist review.

## Known risks to document

- The current model is an initial binary baseline, not a production betting
  system.
- EPL draws are included in not-home-win.
- Good holdout metrics do not prove future profitability.
- Provider data can change, so provenance and hashes must be checked when
  reproducing historical results.
- Deployment and frontend workflows require separate teammate-owned validation.
