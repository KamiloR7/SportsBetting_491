# Sprint 4 Interim SOC 2-Aligned Assessment and Evidence Register

**Prepared:** November 5, 2026  
**Assessment scope:** CC6.1 logical access, based on repository and Jira evidence available to Ayman.  
**Status:** Interim and incomplete. This is a classroom assessment, not a SOC 2 audit, certification, or production assurance statement.

## Summary

The current backend supports account registration and public sports/match browsing. The registration implementation hashes passwords with bcrypt. The inspected API does not define login, session, logout, or authorization middleware, and the sports/match endpoints return public catalog data. The application therefore has no verified protected resource or access-denial behavior to test yet. CC6.1 is **not verified**.

The login prototype correction is available in [PR #35](https://github.com/KamiloR7/SportsBetting_491/pull/35), commit `a9181c28`. The PR removes credential logging and unauthenticated dashboard navigation, clears the password on submit, and displays a notice that the prototype does not authenticate. At the last observed GitHub check, both CI jobs passed and a teammate review was pending. The PR is not evidence of working authentication and must not be counted as a satisfied access control.

## Risk and control register

| Control / risk | Owner and Jira | Implementation / verification | Acceptance criteria | Evidence and current result | Gap and next action |
| --- | --- | --- | --- | --- | --- |
| **CC6.1 — Logical access.** The prior login prototype printed submitted credentials and routed to the dashboard without authentication. The backend currently has registration but no observed login/session flow or protected API resources. | Ayman; [SCRUM-277](https://cpsc-491-group5.atlassian.net/browse/SCRUM-277) | Remove credential logging and misleading success/navigation in the prototype. Inventory actual routes. When protected routes exist, verify server-side authorization with missing, invalid, and valid credentials and ownership/permission checks. | No credentials appear in browser logs; prototype does not claim successful sign-in; every route has an explicit access classification and rationale; protected endpoints deny missing/invalid access without protected data or writes. | PR #35 source change and [CI run](https://github.com/KamiloR7/SportsBetting_491/actions/runs/41003578496) are linked. CI passed at last observation. No browser console test or backend access test was executed for this register. Status: **Partial / not verified**. | Await PR review and merge. Execute synthetic-credential UI check. Reassess route inventory and add protected-resource tests when backend authentication and a private resource are implemented. |
| **CC6.1 — Group access-control assessment.** The group needs reproducible evidence that authentication, authorization, sessions, CSRF, rate limits, and ownership rules operate as designed. | Dang; [SCRUM-281](https://cpsc-491-group5.atlassian.net/browse/SCRUM-281); implementation [SCRUM-180](https://cpsc-491-group5.atlassian.net/browse/SCRUM-180); tests [SCRUM-192](https://cpsc-491-group5.atlassian.net/browse/SCRUM-192); CI/PostgreSQL [SCRUM-191](https://cpsc-491-group5.atlassian.net/browse/SCRUM-191) | Collect the owner’s implementation and test evidence. Required checks include denied/allowed access, bcrypt login, 30-minute expiry and logout revocation, CSRF/cookie flags, account ownership, five failed attempts in five minutes and a 15-minute block, recovery, generic errors, and sanitized logs. | Each check has expected and observed results, reproducible command, timestamp, commit, environment/database, and sanitized evidence link. Isolated PostgreSQL results are separate from SQLite/in-memory/local-only results. | Ticket descriptions define the planned criteria. No execution results or evidence URLs were available during this review. Status: **Not assessed / evidence pending**. | Request and link Dang’s actual test results and CI artifacts. Do not mark a check pass from the ticket plan alone. |

## Backend route inventory from source review

The inventory below is based on route declarations in `backend/app/main.py` and `backend/app/routes/`. No running or deployed API was queried for this register.

| Method and route | Classification | Rationale / current limitation |
| --- | --- | --- |
| `GET /health` | Public | Health status only; no user or protected data returned. |
| `GET /sports` | Public | Sports catalog. |
| `GET /leagues` | Public | League catalog. |
| `GET /teams` | Public | Team catalog. |
| `POST /auth/register` | Public | Account creation must be available before authentication; source hashes passwords with bcrypt. Duplicate email/username conflicts are handled. No login/session endpoint was found. |
| `GET /matches` | Public | Match catalog with optional league/status filters; no account-specific data. |
| `GET /matches/history` | Public | Final match results; no account-specific data. |
| `GET /matches/{match_id}` | Public | Single public match detail. |

**Protected routes found in source:** none.  
**Login/session/logout routes found in source:** none.  
**Ownership/tenant-scoped API resource found in source:** none in the inspected route modules.  

This route inventory is an implementation-source snapshot. It does not prove that a deployed API has the same routes or configuration.

## Evidence ledger and limits

| Evidence | Link / reference | What it supports | What it does not support |
| --- | --- | --- | --- |
| Login prototype code change | [PR #35](https://github.com/KamiloR7/SportsBetting_491/pull/35), commit `a9181c28` | Submitted email/password no longer logged; submit no longer routes to dashboard; password is cleared; notice clarifies no authentication. | Working login, session management, protected routes, or server-side authorization. |
| PR CI | [GitHub Actions run](https://github.com/KamiloR7/SportsBetting_491/actions/runs/41003578496) | At last observed status, frontend CI and build checks passed. | Manual browser verification, PostgreSQL-backed access tests, or deployed HTTPS behavior. |
| Backend source review | `backend/app/main.py`, `backend/app/routes/auth.py`, `backend/app/routes/sports.py`, `backend/app/routes/matches.py` | Route declarations and bcrypt registration implementation visible in the reviewed checkout. | Runtime/deployed API behavior or unreviewed commits. |
| Midterm report / prior proposal | Individual SOC 2 proposal and midterm-derived baseline | Starting design context. | Current sprint test execution. |

No real credentials or production data were used. No tests were executed while preparing this interim register. CI details above reflect the previously observed PR state and should be refreshed before final submission.

## Required follow-up before any control can be marked satisfied

1. Review and merge PR #35 after teammate review; retain the final commit and CI links.
2. Run a browser console check with synthetic credentials and retain a sanitized screenshot or check log.
3. Have the backend owner document the implemented authentication/session and protected-resource design, if it now exists.
4. Execute missing/invalid/valid credential, logout/expiry, ownership, CSRF/cookie, rate-limit, and generic-error checks against the intended environment. Record skipped cases as blocked or not run.
5. Attach PostgreSQL-backed evidence and identify the exact commit, workflow run, and environment.
6. Obtain the other control owners’ actual outcomes before completing the group register. Until then, their controls remain evidence-pending.
