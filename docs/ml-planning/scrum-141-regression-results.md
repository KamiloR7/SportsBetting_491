# SCRUM-141 Final Regression Results

Execution date: 2026-11-19  
Commit under test: `2f184ff` (`origin/aymoon13/sprint3-model-loading`)  
Runtime: Python 3.12.15 on macOS arm64

## Results

| Check | Result |
| --- | --- |
| Python regression suite (`backend/tests` and `tests`) | **361 passed** in 30.14 seconds |
| ML module coverage | **82%** (385 of 470 statements covered) |
| Python compile check (`backend`, `src`, `tests`) | Passed |
| Python wheel build | Passed; `sportsbetting_491-0.1.0-py3-none-any.whl`, SHA-256 `a5bdbcde20910afdbbe41a3c654157a4a836573991efa87e9937e302441394dc` |

The test run emitted three `DeprecationWarning` messages from SQLAlchemy's SQLite
datetime adapter in the Sprint 3 flow tests. They did not fail the suite and
should be addressed in a follow-up dependency or adapter change.

## Reproduction

From the repository root, with Python 3.12 and the project dependencies installed:

```sh
PYTHONPATH=backend python -m pytest backend/tests tests \
  --cov=backend/app/ml \
  --cov-report=term-missing \
  --cov-report=xml:build/coverage.xml \
  --junitxml=build/test-results.xml
python -m compileall -q backend src tests
python -m pip wheel --no-deps . --wheel-dir build/dist
```

Generated JUnit XML, coverage XML, and wheel files were kept in the ignored
`build/` directory. The report records the observed results; it does not claim
that a hosted GitHub Actions run or manual live-service test was performed.
