# SCRUM-77: CI Coverage Reporting

Owner: Andrew Vedder. Review: PR #34, `feature/scrum-77-coverage` into `main`.

## Jira Acceptance Mapping

| Subtask | Implementation | Verification |
| --- | --- | --- |
| SCRUM-87: Configure Python coverage/pytest coverage | `.coveragerc` enables line and branch measurement for `backend/app` and `src/sportsbetting`; CI installs pytest-cov. | The reporting integration test uses the actual repository configuration, including an unimported namespace module. |
| SCRUM-88: Generate coverage results during CI | Existing pytest run produces terminal, Cobertura XML, and HTML reports. | Integration tests verify XML totals, uncovered files, HTML index, and JUnit output for passing and failing suites. |
| SCRUM-89: Display coverage percentage in workflow output | The test log shows coverage; the build job summary includes a Markdown per-file table and total. | Integration tests run the actual Markdown renderer; the Actions run provides the final hosted evidence. |
| SCRUM-90: Verify reporting with the existing test suite | Coverage runs around the complete existing pytest suite. | Review the build job's test result, summary, and downloadable `coverage-<build-id>` artifact. |

## What Is Measured

Line coverage identifies executed statements. Branch coverage also checks the
alternative paths through decisions. The terminal and Markdown `Cover` column
combine line and branch opportunities; XML exposes the separate rates.
Unimported modules, including namespace-package modules without `__init__.py`,
remain in the denominator rather than disappearing from the report.

Frontend JavaScript, root-level standalone collectors, migration files outside
the measured directories, and this test infrastructure are outside this scope.
There is no minimum percentage requirement in this story. The report exposes
gaps for the team to prioritize without adding an arbitrary quality gate.

## Review in GitHub

1. Open PR #34 and follow its **build** check to the Actions run.
2. Check **Run automated tests** for the test count and coverage totals.
3. Open the run summary to inspect **Python line and branch coverage**.
4. Download `coverage-<build-id>` from the run's artifacts. Open
   `coverage-html/index.html` to inspect missing lines and branches by file;
   use `coverage.xml` with tools that consume Cobertura reports.
5. Confirm both the backend build and frontend checks finish successfully.

Coverage reports are retained for 30 days. JUnit results remain in the separate
test artifact; build metadata identifies the source commit for each run.

## Recorded Verification

Local verification on October 15, 2026, using Python 3.14.4, pytest 9.1.1,
pytest-cov 7.1.0, and coverage.py 7.16.2:

| Check | Result |
| --- | --- |
| Complete existing suite plus reporting tests | 490 passed, 4 skipped, zero failures/errors |
| Separate line coverage from XML | 1,303 / 1,802 statements, 72.31% |
| Separate branch coverage from XML | 373 / 542 destinations, 68.82% |
| Combined terminal/Markdown coverage | 71.50% |
| Passing and failing subprocess report checks | Both passed |
| XML, HTML index, JUnit, and Markdown output | Generated and verified |

The initial PR commit's [hosted Actions run](https://github.com/KamiloR7/SportsBetting_491/actions/runs/38846405873)
passed both jobs and uploaded its coverage artifact. Follow PR #34's latest
checks for the updated branch-coverage run. Percentages can vary as code and
tests change. The earlier 82.05% measured lines with narrower file discovery;
it is not directly comparable to the current total, which includes branch
paths and previously undiscovered namespace files.

## Repeat Locally

Install dependencies and set `PYTHONPATH` as described in the root README. Run
the documented coverage command from the repository root, then:

```bash
python -m coverage report --format=markdown
python -m pytest tests/test_coverage_reporting.py -v
```

The two reporting tests create isolated temporary projects and run real pytest
and coverage subprocesses. One suite passes and one deliberately fails after
executing code. Both must produce valid XML, HTML, JUnit, and Markdown reports;
the failing suite must retain exit code 1. Their temporary coverage databases
are isolated from the application's coverage data.

The workflow attempts summary publication and artifact upload after either a
passing or failing test step. Missing data causes reporting errors instead of
silently skipping the summary. Dependency/setup failures skip those steps
because no test run occurred. Collection failures may prevent report creation;
the failed workflow and reporting errors expose that condition.
