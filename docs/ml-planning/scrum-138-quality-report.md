# SCRUM-138 Evaluation Quality Report

## Decision policy

Compare Brier score and log loss to the training-prevalence baseline computed
from the training split. For each loss, a lower model value is `PASS`, a higher
value is `FAIL`, and a tie within `1e-12` is `WARNING`. The combined decision is
`PASS` when both losses improve, `FAIL` when both get worse, and `WARNING` when
the evidence is mixed or tied. Classification metrics remain descriptive; this
policy does not invent a universal accuracy target across sports.

The evaluator rejects nonfinite probability arrays and nonfinite loss values.
Evaluation JSON is serialized with NaN/Infinity disallowed so invalid reports
cannot be written as apparently valid JSON.

## Existing cached-data metric summary

The values below were read from `sprint2_real_data_results.json`, source commit
`9e1e1f781d2f2de9bf7ddf3adfd47e52eca897cf`, and assessed with the policy above.
They are a repeatable assessment of the recorded held-out results, not a new
download or retraining run.

| Sport | Test rows | Accuracy | Model Brier | Baseline Brier | Model log loss | Baseline log loss | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| NFL | 107 | 0.6636 | 0.221847 | 0.249132 | 0.635112 | 0.691412 | PASS |
| MLB | 482 | 0.5519 | 0.246868 | 0.250097 | 0.686847 | 0.693343 | PASS |
| EPL | 151 | 0.6556 | 0.210052 | 0.246055 | 0.605057 | 0.685236 | PASS |

These relative results do not establish future predictive performance or
betting profitability. The hosted CI run for the pull request is the pending
linkable validation evidence; local targeted regression evidence is recorded in
the PR description.
