# SportsBetting_491


## Testing and CI

### Run tests locally

Create and activate a Python virtual environment, then install the project and test dependencies:

```bash
python -m pip install -e .
python -m pip install -r backend/requirements.txt "pytest-cov>=7,<8"
```

Set `PYTHONPATH=backend` in your shell, then run:

```bash
python -m pytest -v
```

### Coverage reporting (SCRUM-77)

Run the same coverage command used by CI from the repository root:

```bash
python -m pytest -v --junitxml=build/test-results.xml --cov --cov-config=.coveragerc --cov-report=term-missing --cov-report=xml --cov-report=html
```

`.coveragerc` measures Python line and branch coverage across `backend/app` and
`src/sportsbetting`, including namespace-package files that tests do not import. The percentage
does not include the frontend or standalone collector scripts at the repo root.
There is no minimum coverage gate yet; test failures still fail CI.

Each pull request targeting `main` publishes a per-file coverage table and total
percentage in the GitHub Actions **build** job summary and test log. Download the
`coverage-<build-id>` artifact for `coverage.xml` and the browsable HTML report
(`coverage-html/index.html`). Reports are retained for 30 days and uploaded even
when tests fail, when pytest was able to generate them. Missing reports fail the
reporting steps after a test run. Local reports are written under `build/`.

The summary's `Cover` column combines covered lines and branch destinations;
XML reports also expose separate line and branch rates. Branch coverage shows
whether both paths of a decision were exercised.

See [SCRUM-77 verification and Jira mapping](docs/ci-coverage-verification.md)
for the acceptance checks, report locations, and failure-case verification.
