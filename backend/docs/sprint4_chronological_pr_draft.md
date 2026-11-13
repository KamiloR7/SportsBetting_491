# Sprint 4: Add chronological dataset preparation and validation

Proceeding without a Jira issue key, as authorized by Kamilo Ramirez.

Canonical Sprint 3 history lacks an explicit chronological ML projection that
retains source identity and checks result availability. Add an offline builder
for completed single-provider NFL, MLB, and EPL history. It preserves explicit
season provenance, splits whole UTC kickoff dates, and rejects training labels
or prior-day historical results unavailable at the relevant prediction cutoffs.
For example, a training result published after the earliest held-out prediction
now rejects the dataset even when that match involves unrelated teams.

Reuse the Sprint 3 integrity gate, timestamp validators and chronological splitter.
Add synthetic regression tests covering determinism, duplicates, invalid input,
season provenance, same-day exclusion, rolling-test history, and future-score
invariance. Document the fail-closed policy and downstream feature allowlists.
Existing training/API behavior and canonical normalization contracts are unchanged.

Validation against main at `7b31053`:

- 38 dataset tests passed.
- Full guarded offline regression: 547 passed, 0 failed, 4 skipped.
- Both previously failing coverage-report tests passed after CI-required
  pytest-cov 7.1.0 and coverage 7.17.2 were installed in an isolated temporary
  environment. Shared dependencies and tracked requirements were unchanged.
- Skips: PostgreSQL integration requires a disposable database.
- Python compilation and whitespace checks passed.

No real historical files or verified result-availability provenance were
available, so no real-data model metrics are claimed. This produces raw match
partitions, not new prediction features or models. Training integration remains
separate work. Review timestamp provenance and the single-provider history policy
with the ML/data teammate. Real-data acceptance remains blocked by missing
historical files and verified availability provenance. PostgreSQL integration
was skipped and hosted CI verification is still required. Implementation is
ready for commit and peer review.
