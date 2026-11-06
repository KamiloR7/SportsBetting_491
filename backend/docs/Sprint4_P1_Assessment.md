# Sprint 4 P1 — Prediction Processing Input Integrity assessment

Student: Kamilo Ramirez, Group 5, CPSC 491-05. Assigned criterion: PI1.2.
This is a local engineering assessment, **not SOC 2 certification or a claim of
full control compliance**. Date context: 2026-11-05, America/Los_Angeles.

## Acceptance source and scope

Source of truth: the exact criteria Kamilo supplied in conversation from
**Sprint 4 — Individual SOC 2 Security Compliance Proposal**. The original PDF
was uploaded in another conversation and was not available in this checkout;
no claim is made that its unseen content was reviewed. The supplied criteria are:

- **P1.1 — Input Validation:** All 12 invalid-input scenarios must be rejected
  before model execution.
- **P1.2 — Historical Data Integrity:** Zero future-dated historical records may
  enter the prediction model.
- **P1.3 — Prediction Consistency:** Ten repeated executions per accepted fixture
  must preserve input hashes, feature order, and model versions. Probabilities
  must be valid and sum to 1 within 0.000001.
- **P1.4 — EPL Transparency:** EPL predictions must clearly disclose estimated
  draw/away probabilities in both API and frontend. Unsupported configurations
  must fail clearly. Direct three-class outputs must not be mislabeled estimates.
- **Additional freshness requirement:** proposed 24-hour source freshness for
  upcoming-match prediction data.
- **Required evidence:** automated results, sanitized logs, screenshots, GitHub
  commits/PRs and documented verification results. Each criterion is classified
  Verified, Failed, Partially Verified or Not Yet Tested.

Assessment scope is the prepared-feature interface, its upstream historical/ML
pipeline, and probability disclosure across current legacy/frontend paths.
All model/record fixtures are controlled synthetic engineering fixtures. No
real historical data, production model, production request or actual predictive
accuracy is represented. Statuses below describe executed evidence, not the
mere existence of test code. Application-wide gaps are explicitly retained.

## Branch and prerequisites

Branch `member3/sprint4-soc2-p1-integrity`, isolated worktree
`/private/tmp/SportsBetting_491-sprint4-p1`, based on `54d8501`.
The executed assessment used the `54d8501` source tree, originally based on
main `7b31053`. Publication-time refresh found origin/main at `e8b92b0` after the
separate authentication PR merged. That newer main was not merged into this
contribution and its authentication changes are not covered by these results.

PRs [#43](https://github.com/KamiloR7/SportsBetting_491/pull/43),
[#44](https://github.com/KamiloR7/SportsBetting_491/pull/44),
[#45](https://github.com/KamiloR7/SportsBetting_491/pull/45), and
[#46](https://github.com/KamiloR7/SportsBetting_491/pull/46) remain open.
[#47](https://github.com/KamiloR7/SportsBetting_491/pull/47) has merged into
`member3/sprint4-ml-training` at `a35866e`. That merge has the same source tree
as the tested `54d8501` base, verified with an empty tree diff. The correct
stacked PR target is therefore `member3/sprint4-ml-training`; no rebase or merge
is needed to publish the P1-only diff. No Jira key is used.

At original evidence capture this contribution had no commit/PR. Publication
and independent review are still separate evidence steps. Prior PRs are
prerequisites, not approval evidence for this assessment.

## Assessment matrix

| Criterion and objective | Executed procedure and expected result | Actual result and evidence | Status | Remaining remediation |
| --- | --- | --- | --- | --- |
| P1.1: reject invalid prepared inputs | 12 distinct adversarial HTTP requests; spy on inference entry and actual sklearn `predict_proba`; expect structured 422/409, zero executions and no predictions | 12/12 returned their expected code/status, inference calls=0, model executions=0, prediction_generated=false. [assessment-results.json](qa/sprint4-p1/assessment-results.json), `test_p1_1_twelve_http_rejections_precede_model_execution`, [rejection log](qa/sprint4-p1/rejection-events.jsonl) | **Verified**, for the 12 selected prepared-endpoint scenarios | Independent review, screenshots and deployment-level evidence remain outstanding. This does not extend the new contract to legacy match-ID endpoints or exhaust every possible malformed input. |
| P1.2: prevent future/target historical information | Reject same-day/future/target/unavailable evidence before execution; change future score and compare earlier predictors/probabilities; verify rolling history and delayed-result rejection | Four temporal/identity attacks rejected with zero model executions; future-score invariance and rolling 24→25 observations verified; unavailable prior result rejected. JSON `leakage`, `test_p1_2_*`, existing chronological/feature suites | **Partially Verified** | Controlled paths pass, but prepared numeric features/timestamps remain caller assertions; no verified real archive or availability provenance exists. Legacy DB queries do not establish result availability. Complete source-backed and application-wide verification. |
| P1.3: reproducible processing | 10 actual sklearn executions for each accepted NFL/MLB/EPL fixture under fixed configuration; compare canonical hashes, columns observed at `predict_proba`, versions and probability vectors | 30 actual model executions; each sport has one input hash, one ordered feature schema, one model version and one probability vector; all distributions valid at 0.000001. JSON `consistency`, `test_p1_3_*` | **Verified**, for the three controlled fixtures | No implication of production accuracy, calibration, cross-library/hardware bitwise equivalence or real-data completeness. Peer review/published evidence pending. |
| P1.4: truthful EPL probability disclosure | Distinguish direct binary, direct multiclass and legacy estimated split; verify API metadata, frontend messages, uncalibrated note and unsupported-mode errors | API tests verify estimated draw/away labels for legacy split and no estimate labels for direct EPL; eight frontend tests pass; lint/build pass. JSON `transparency`, Python `test_p1_4_*`, frontend TAP | **Partially Verified** | Browser capture was not approved, so rendered visual/interaction screenshots are absent. Frontend owner review and representative end-to-end estimated/direct UI flows still needed. Current frontend fetches the binary endpoint; other disclosures are supported by the shared renderer but not live-wired to a new match resolver. |
| Upcoming data freshness | Missing source evidence fails; exact 24h allowed; 24h+1µs rejects; old feature cutoff cannot bypass processing-time age; looser configuration cannot weaken cap | Boundary and bypass tests pass; absent observation yields freshness_unavailable; stale yields stale_source. JSON `freshness`, `test_upcoming_*` | **Partially Verified** | No independently trustworthy provider observation timestamp exists in the current API; it is supplied by the caller. Validate genuine source timestamps, source completeness and operational monitoring before claiming actual source freshness. |

Overall P1 assessment: **Partially Verified**. No criterion is claimed Failed
based on the final executed suite, but external provenance, screenshots,
frontend owner approval, PostgreSQL execution, own commit/PR review, and hosted
CI remain incomplete. Verified rows are narrowly scoped engineering acceptance.

## P1.1 scenario inventory: expected versus observed

All scenarios use the real prepared HTTP contract and controlled local models.
Invalid numeric infinity is deliberately submitted as an adversarial JSON token
that Python's JSON decoder accepts, then rejected by numeric validation. Valid
missing-history null/NaN means remain accepted and are not substituted with a
blanket non-finite rejection rule.

| ID | Scenario | Expected / actual HTTP | Expected / actual error code | Model calls / predictions |
| --- | --- | --- | --- | --- |
| P1.1-01 | Unsupported sport | 422 / 422 | invalid_request / invalid_request | 0 / none |
| P1.1-02 | Missing required predictor | 422 / 422 | invalid_features / invalid_features | 0 / none |
| P1.1-03 | Incorrect numeric type | 422 / 422 | invalid_request / invalid_request | 0 / none |
| P1.1-04 | Infinite scoring value | 422 / 422 | invalid_features_or_cutoff / invalid_features_or_cutoff | 0 / none |
| P1.1-05 | Incorrect declared feature order | 409 / 409 | feature_schema_mismatch / feature_schema_mismatch | 0 / none |
| P1.1-06 | Incompatible feature schema | 409 / 409 | feature_schema_mismatch / feature_schema_mismatch | 0 / none |
| P1.1-07 | Requested model version mismatch | 409 / 409 | model_version_mismatch / model_version_mismatch | 0 / none |
| P1.1-08 | Feature cutoff at kickoff | 422 / 422 | invalid_features_or_cutoff / invalid_features_or_cutoff | 0 / none |
| P1.1-09 | Historical result unavailable by cutoff | 422 / 422 | historical_cutoff_violation / historical_cutoff_violation | 0 / none |
| P1.1-10 | Upcoming source older than 24h | 422 / 422 | stale_source / stale_source | 0 / none |
| P1.1-11 | Blank match identity | 422 / 422 | invalid_request / invalid_request | 0 / none |
| P1.1-12 | Unapproved prediction configuration | 422 / 422 | invalid_request / invalid_request | 0 / none |

The scenario fixture for P1.1-08 processes at kickoff to isolate the strict
pre-kickoff constraint rather than triggering the earlier processing-time guard.
Other temporal attacks separately cover future processing cutoffs. Evidence
contains the measured codes, counts and flags rather than only expected values.

## Production changes and reuse

Existing code already supplied supported-sport/type/schema checks, exact ordered
allowlists, missingness-aware numeric checks, input consistency, temporal
provenance checks, model-version pinning, trusted-local loading, training-label
cutoffs, integrity fingerprints and normalized probabilities. Those checks are
reused; their existence alone is not substituted for execution evidence.

New checks/disclosures:

- `canonical_prediction_input_hash` and response `input_sha256` bind semantic
  prepared inputs to a deterministic SHA-256. UTC instants, numeric forms,
  null/NaN means and mapping/evidence ordering normalize; declared feature order
  stays significant. Processing time is excluded. No raw input data is logged.
- Upcoming requests require source observation and an age no greater than 24h
  **relative to prediction processing time**, not a possibly old feature cutoff.
  Optional tighter limits are respected; looser limits cannot disable the cap.
  Historical replay retains its explicitly configured cutoff-based policy.
  Responses disclose applied limit and reference; absent evidence fails clearly.
- API responses disclose `probability_method`, `estimated_outcomes` and
  `probability_calibration="uncalibrated"`. Legacy estimated EPL responses also
  include sport for correct frontend interpretation. Legacy probability outputs
  now pass the shared sport distribution validator; unsupported sports reject.
- The frontend consumes those disclosures, labels estimates and uncalibrated
  output, renders direct EPL draws without calling them heuristic, and fails
  clearly on missing/inconsistent/unsupported configurations. Its endpoint
  selection is unchanged; no invented match resolver or synthetic production
  artifact is introduced. Existing outcome decisions are honored on ties.

## Probability-method inventory

| Endpoint | Actual generation | Disclosure |
| --- | --- | --- |
| POST /predictions | Direct binary home-win/not-home-win, including EPL | direct_binary, estimated_outcomes=[]; UI explains draw/away are not separately modeled |
| POST /predictions/matches/{match_id}, EPL | Binary home/not-home probability; historical smoothed draw share splits not-home mass | estimated_epl_split, estimated_outcomes=[draw, away_win] |
| POST /predictions/matches/{match_id}, NFL/MLB | Direct binary winner probability | direct_binary, no estimated outcomes |
| POST /predictions/prepared, EPL | Trained native three-class logistic regression | direct_multiclass, no estimated outcomes |
| POST /predictions/prepared, NFL/MLB | Trained direct binary logistic regression | direct_binary, no estimated outcomes |

All are explicitly uncalibrated. A probability sum check is not a calibration
assessment. Frontend owner review is required for these rendering/API additions;
no teammate has been contacted or approval invented during this task.

## Evidence and verification

- Backend final regression: **744 passed, 0 failed, 4 skipped**, under the
  existing SCRUM-203 network/PostgreSQL guard. Includes **30 new P1 tests**.
- Focused P1/chronological/feature/interface/legacy run: 155 passed before the
  final instrumented feature-column spy and one route disclosure test; the full
  regression above includes both final changes.
- Frontend: **8 passed, 0 failed, 0 skipped**; ESLint and production build passed.
- Python compilation and whitespace checks passed. No Python lint/type-check
  command is configured. Four PostgreSQL tests were not run; no actual database
  persistence/integration claim is made.
- No credentials, tokens, request bodies, real user records, hostnames, absolute
  machine paths or raw tracebacks are copied into committed-intended evidence.
  Model/input hashes and probability vectors in JSON are synthetic fixture data.

| Required evidence | Reference | Availability |
| --- | --- | --- |
| Automated backend results | [sanitized JUnit](qa/sprint4-p1/backend-regression.xml) | Verified, 744/0/4 |
| Measured P1 observations | [assessment JSON](qa/sprint4-p1/assessment-results.json) | Verified, actual fixture observations |
| Sanitized rejection logs | [JSONL events](qa/sprint4-p1/rejection-events.jsonl) | Verified, generated from observed test events; not production audit logs |
| Frontend test results | [TAP](qa/sprint4-p1/frontend-tests.tap) | Verified, 8/0/0 |
| Runtime/check summary | [verification JSON](qa/sprint4-p1/verification.json) | Verified local checks, not hosted CI |
| Source snapshot | [source manifest](qa/sprint4-p1/source-manifest.json) | Uncommitted file hashes bind this review snapshot |
| Screenshots / rendered UI | Not captured: browser host unavailable, Safari access not approved | **Not Yet Tested** |
| Own GitHub commit and reviewed PR | Not available at original assessment capture; attach the published contribution and independent review when available | **Not Yet Tested** |

## Reproduction and remaining work

From repository root with the existing backend/ML dependencies and CI coverage
packages installed:

```bash
P1_EVIDENCE_OUTPUT=/private/tmp/p1-assessment.json PYTHONPATH=.:backend:src \
  python -m pytest -q backend/tests/test_soc2_p1_integrity.py
PYTHONPATH=.:backend:src python -m pytest -q --junitxml=/private/tmp/p1-regression.xml
python backend/docs/qa/sprint4-p1/sanitize_evidence.py \
  --assessment /private/tmp/p1-assessment.json --junit /private/tmp/p1-regression.xml \
  --output /private/tmp/p1-sanitized
cd frontend
npm ci --ignore-scripts --no-audit --no-fund
npm run test:p1
npm run lint
npm run build
```

Raw pytest XML may include local details and must not be published directly;
the sanitizer copies only test identities/status, never captured output. To
repeat the connection-prohibited audit, invoke the existing offline guard before
pytest as done in the execution record. Current raw outputs are temporary local
files; only the sanitized projections are intended for peer review.

Remaining remediation: supply genuine source/availability evidence; complete
source-backed and legacy-path leakage assessment; obtain authorized screenshots
of estimated/direct disclosure and rejection flows; coordinate frontend owner
review and representative UI integration; run disposable PostgreSQL tests;
create/review this contribution's commit and stacked PR after technical review;
run hosted CI or an approved equivalent for the stacked base. This document
records the executed assessment snapshot; publication/review status must be
checked on the eventual P1 PR. No prior worktree or stash was changed.
