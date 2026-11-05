# Sprint 4 CC6.1 assessment

**Owner:** Dang Nguyen, CPSC 491-05 Group 5. **Assessment date:** November 5, 2026.

The synthetic backend assessment demonstrates the proposed authentication,
session, CSRF, throttling and ownership behavior. All 65 security/policy cases
passed locally, including actual isolated PostgreSQL tests; the full regression
passed 555 tests with four pre-existing historical-import PostgreSQL tests
skipped. Real loopback HTTPS checks also passed. **Peer approval, frontend
integration, merged-main CI and the individual document submission remain open.**

## Scope and traceability

- Tested implementation commit: [`2a4223e3243aa97944bf3dfdfc0c86cab9b03c9c`](https://github.com/KamiloR7/SportsBetting_491/commit/2a4223e3243aa97944bf3dfdfc0c86cab9b03c9c).
- Baseline commit: `25cc7cf1ebc4dab95873adfe403216d174198349`; unchanged baseline was 490 passed, four skipped.
- Environment and exact package versions: [run summary](evidence/run-summary.json).
- Databases: per-test ephemeral SQLite and random isolated schemas in a local
  PostgreSQL 17 database named `sportsbetting_sprint4_test`. No real account,
  provider, shared developer or production data was used.
- HTTPS evidence uses a real temporary loopback server, a generated explicitly
  verified test certificate and ephemeral SQLite. It separately validates
  transport/cookie behavior; it is not the PostgreSQL result.
- Route surface: [24 method/route pairs](evidence/route-inventory.json), four
  protected. Public match history/inference remains public. Synthetic ownership
  endpoints are disabled by default and are not real prediction history.

## Observed criterion results

These are observed results in the named environments. Group acceptance and
closure still require the assigned peer review and an evidence disposition.

| Criterion | Observed result | Evidence and practical limit |
| --- | --- | --- |
| U1.1 | Pass in assessed environments | Every protected route rejects anonymous, tampered, expired and logged-out sessions; authorized access succeeds; unauthorized ownership access is 403 and protected records remain unchanged. `test_u11_*`, `test_u13_cross_account_*`, route-policy tests. |
| U1.2 | Pass in assessed environments | Real bcrypt login, correct/wrong credentials, generic errors, controlled-clock 30-minute expiry, rotation, active-account checks and immediate logout replay denial. `test_u12_*`; registration-to-login integration on both databases. |
| U1.3 | Pass for synthetic resources | Missing/invalid/cross-session CSRF rejected; cross-account reads/writes denied; Secure/HttpOnly/SameSite=Strict cookies checked in ASGI and actual verified TLS. `test_u13_*` and [HTTPS evidence](evidence/tls-smoke.json). Real private prediction history remains unimplemented. |
| U1.4 | Pass in assessed environments | Five failures in a rolling five-minute window cause a 15-minute block; boundary/recovery, account-key consistency and successful reset verified. Seven concurrent PostgreSQL attempts yield five 401 responses and two 429 responses. Hash storage, byte limits and sanitized logs/errors checked. `test_u14_*`. |

The password log in the existing React prototype was removed. That page still
navigates without establishing a backend session; it must not be presented as
completed login integration. Backend private access does not rely on that UI.

## Evidence and reproduction

| Evidence | Contents |
| --- | --- |
| [Full regression JUnit](evidence/regression.xml) | 559 cases: 555 passed, four legacy skips, zero failures/errors. |
| [Security JUnit subset](evidence/auth-results.xml) | 65 passed, zero skips/failures/errors; extracted without changing outcomes from the full committed regression. The dedicated CI job runs these test modules directly. |
| [HTTPS smoke](evidence/tls-smoke.json) | Verified real TLS, login, cookies, allowed/denied access, CSRF and logout checks; no raw tokens or passwords. |
| [Route inventory](evidence/route-inventory.json) | Method, path, public/protected classification and rationale. |
| [Run summary](evidence/run-summary.json) | Commit, UTC capture time, package/database environment, result counts and outstanding requirements. |

Commands, isolation guards, schema setup and the frontend contract are in the
[runbook](README.md). The new `auth-security` GitHub Actions job provisions
PostgreSQL, requires the integration cases, runs the HTTPS smoke, and uploads
evidence under `sprint4-auth-<commit>`. Consult the pull request's actual checks
for hosted results; workflow configuration alone is not execution evidence.

## Jira completion record

Implementation is tracked in [SCRUM-180](https://cpsc-491-group5.atlassian.net/browse/SCRUM-180),
CI in [SCRUM-191](https://cpsc-491-group5.atlassian.net/browse/SCRUM-191), testing in
[SCRUM-192](https://cpsc-491-group5.atlassian.net/browse/SCRUM-192), and assessment in
[SCRUM-281](https://cpsc-491-group5.atlassian.net/browse/SCRUM-281). Their subtask
counts remain five, four, four and zero. Evidence review and remaining completion
conditions must be resolved before closing the corresponding parent task.

## Remaining gaps and follow-up

| Gap | Impact and owner | Required action and retest |
| --- | --- | --- |
| Ayman review and policy agreement | Assessment/review pending; Ayman and Dang | Review implementation, access matrix, tests and sanitized evidence; Dang addresses feedback and reruns affected checks before merge. |
| Merged-main CI | SCRUM-202 full done condition pending; Dang after reviewed merge | Preserve required checks, merge only after approval, and record the passing main run. |
| Frontend/session and monitoring handoff | UI still prototype; Ayman with Dang | Integrate same-origin HTTPS login/logout/CSRF; agree telemetry collector boundary/redaction and verify UI behavior. CC7.2 remains Ayman's control. |
| Private production history | Not implemented or secured; Dang/team at next scope planning | Agree retained schema/ownership feature and target sprint, then repeat access/write tests against the real feature. Synthetic assessment records are the current ownership evidence. |
| Four legacy historical-import PostgreSQL cases | Not run in this local assessment; existing importer owner/team | Configure their separately guarded `sportsbetting_data25_test` environment and execute when completing that ingestion scope. They are not Sprint 4 auth passes. |
| Production abuse/retention/deployment | Prototype limitations; team before production | Add recovery and additional traffic controls for account-lockout abuse, retention for challenges/unknown keys, trusted proxy/TLS configuration and production testing. |
| Individual Google Doc and review contribution | Submission not completed here; Dang | Add the actual results/links and limitations through the individual document's native version history, record Dang's review of Kamilo, and submit the required link. |

This is a scoped classroom control assessment. Passing synthetic tests does not
establish production protection, certification or completed peer approval.
