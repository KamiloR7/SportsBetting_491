# ML Release Readiness and Data Source Review Checklist

Related Jira: SCRUM-139.

Use this checklist before merging, demoing, or submitting machine learning work.
It is the non-automated testing evidence for Ayman Sadek's ML/data-prediction
responsibility.

## Data source review

- [ ] Source URLs are listed for NFL, MLB, and EPL data.
- [ ] Retrieval date or cached snapshot date is recorded.
- [ ] Row counts are recorded before and after exclusions.
- [ ] Excluded records are explained, including postponed, resumed, postseason,
      missing-score, or duplicate records.
- [ ] Raw data is not committed unless the team has confirmed it is allowed.
- [ ] Provenance or checksum evidence is attached when model results are cited.

## Automated test review

- [ ] `pytest` passes locally for backend and ML tests.
- [ ] GitHub Actions passes on the pull request.
- [ ] CI evidence includes a build ID, run number, commit SHA, and test artifact.
- [ ] New regression tests cover any bug or edge case fixed in the PR.
- [ ] Tests run offline without live sports API calls unless the task is
      explicitly a data refresh task.

## Model result review

- [ ] Accuracy, precision, recall, F1, Brier score, and log loss are reviewed.
- [ ] Results are compared against a simple baseline.
- [ ] Calibration bins are reviewed before making probability claims.
- [ ] EPL is described as home win versus not-home-win, not as a full three-way
      soccer betting model.
- [ ] The write-up states that model performance does not guarantee betting
      profit.

## Prediction contract review

- [ ] Required feature columns are documented.
- [ ] Input validation behavior is documented for missing, negative, nonfinite,
      or out-of-range values.
- [ ] Output columns are documented:
      `predicted_outcome`, `probability_not_home_win`, and
      `probability_home_win`.
- [ ] Backend or frontend consumers know that probabilities correspond to model
      classes `[0, 1]`.

## Evidence to attach

- [ ] Jira ticket link.
- [ ] Pull request link.
- [ ] CI run link.
- [ ] Screenshot or copied output for key manual checks.
- [ ] Short known-risk summary.
