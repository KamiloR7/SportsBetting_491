# SCRUM-59: Downloadable builds and source traceability

The CI Build workflow checks Python and React on pull requests targeting `main`
and pushes to `main`. The Python distribution already had a build artifact.
The React job now also retains the files produced by `npm run build`, including
`index.html`, compiled assets, and `build-info.txt`.

## Find a build

1. Open the pull request's **Checks**, then the **CI Build** workflow run.
2. Confirm that the checks required for the release passed. An artifact's
   existence alone does not establish that every job passed.
3. Download `frontend-build-<run-id>-<attempt>-<short-commit>` from **Artifacts**.
   Frontend artifacts are retained for 30 days. They are uploaded only after the
   frontend lint, build, and metadata packaging steps succeed.
4. Read the included `build-info.txt` before using the files for a demonstration.
   Record its build ID and workflow run URL alongside screenshots or video.

The Python build and its existing test/coverage artifacts continue using the
same build ID convention. The shared metadata helper gives both build jobs the
same ID for a given workflow run, attempt, and checkout. A rerun receives a
different attempt number and therefore a different ID.

## Identify the source that was built

| Metadata field | Meaning |
| --- | --- |
| `build_id` | Workflow run ID, run attempt, and the first seven characters of the checked-out commit. |
| `commit`, `short_commit` | Actual Git checkout used by the job. |
| `source_commit` | Pull request head commit, or event commit for a push. |
| `branch` | Pull request source branch, or pushed branch. |
| `run_id`, `run_attempt`, `run_number` | GitHub's workflow execution identifiers. |
| `repository`, `event`, `run_url`, `created_utc` | Repository, triggering event, workflow evidence URL, and UTC metadata creation time. |

GitHub's default pull request checkout builds a merge commit. Its SHA can differ
from the pull request head SHA. Both values are recorded so reviewers can
distinguish the proposed source from the exact revision that CI built.
Creation timestamps may differ between jobs; the build ID and checked-out
commit identify their shared revision.

The uploaded frontend is a build output for review and demonstration setup.
It still needs the configured backend and normal application runtime settings;
publishing the artifact does not deploy the application.

## Local validation, 2026-11-19 UTC

The workflow YAML parsed successfully, Bash syntax checks passed, and the
metadata helper passed 84 assertions in isolated temporary Git repositories.
These checks covered differing pull request head/merge commits, matching job
IDs, rerun uniqueness, push metadata, required inputs, and literal branch text.
`git diff --check` also passed. These local checks do not execute GitHub Actions
or prove a React artifact upload; confirm the PR's workflow run and download
the artifact to finish that verification.
