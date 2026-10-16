# Member 1 Sprint 3 Jira Alignment

This file maps the original Member 1 Backend and Database plan to the live Sprint 3 Jira issues. All eight issues are assigned to Ayman Sadek, included in `SCRUM Sprint 3`, and placed in `In Review`. Do not mark an issue Done until its remaining PR, CI, review, and manual evidence is attached.

| Ticket | Scope and acceptance criteria | Repository evidence | Current status |
| --- | --- | --- | --- |
| [SCRUM-261](https://cpsc-491-group5.atlassian.net/browse/SCRUM-261) Model loading | Load one trusted NFL, MLB, and EPL artifact; verify checksum and metadata; reject missing or ambiguous deployments; cache loaded models. | `backend/app/services/model_registry.py`; model registry tests; commit `3d392ce`; [PR #29](https://github.com/KamiloR7/SportsBetting_491/pull/29) | In Review; CI and approval pending |
| [SCRUM-266](https://cpsc-491-group5.atlassian.net/browse/SCRUM-266) Prediction service and endpoint | Accept a selected match ID; identify its sport; route through the correct model; expose `POST /predictions`. | Prediction route, schema, and service; commit `3a47b96`; [PR #29](https://github.com/KamiloR7/SportsBetting_491/pull/29) | In Review; CI and approval pending |
| [SCRUM-262](https://cpsc-491-group5.atlassian.net/browse/SCRUM-262) Team and history lookup | Query the selected matchup and only final games before its start time; calculate win rate, scoring average, and average allowed. | `MatchHistoryRepository`; automated history tests | In Review; PR evidence pending |
| [SCRUM-263](https://cpsc-491-group5.atlassian.net/browse/SCRUM-263) Validation and error handling | Reject missing, invalid, and extra request fields; return controlled 404, 422, and 503 responses. | Prediction API integration tests | In Review; PR evidence pending |
| [SCRUM-268](https://cpsc-491-group5.atlassian.net/browse/SCRUM-268) Standard response and probabilities | Return the same schema for NFL, MLB, and EPL with home-win and not-home-win probabilities, confidence, model version, and history counts. | Prediction response schemas and parameterized sport tests | In Review; PR evidence pending |
| [SCRUM-267](https://cpsc-491-group5.atlassian.net/browse/SCRUM-267) Backend integration tests and CI | Cover successful and negative paths; run the full Python suite and frontend lint/build on every PR to main. | 136 local tests; updated `.github/workflows/ci.yml` | In Review; hosted CI pending |
| [SCRUM-264](https://cpsc-491-group5.atlassian.net/browse/SCRUM-264) API and frontend integration | Document the API; let the match-details page request and display prediction results, errors, confidence, and history counts. | Backend README; frontend prediction service and panel | In Review; manual browser test pending |
| [SCRUM-265](https://cpsc-491-group5.atlassian.net/browse/SCRUM-265) Sprint artifacts | Complete the final test plan, manual results workbook, PR links, review/approval link, CI link, Jira links, and work-day evidence. | Files under `docs/sprint3`; combined PR to be opened in class | In Review; external evidence pending |

## Jira issue requirements

Each live issue should contain:

- a description matching the delivered code;
- acceptance criteria from the table above;
- the feature branch and relevant commit;
- the combined pull request after it is opened;
- the successful CI run and teammate approval after they exist;
- the automated or manual test evidence; and
- a final status that reflects reality.

## Items that cannot be completed locally

- Link the combined Sprint 3 pull request to each applicable issue.
- Obtain a teammate review and approval.
- Wait for both GitHub Actions jobs to pass, then merge through the PR.
- Run and record the live PostgreSQL/model/browser manual cases.
- Demonstrate five distinct real work dates. Current Git evidence shows Member 1 Sprint 3 activity on 8 October 2026 and 15 October 2026 only.
