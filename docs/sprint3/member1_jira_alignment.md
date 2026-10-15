# Member 1 Sprint 3 Jira Alignment

This file translates the original Member 1 Backend and Database plan into ticket-ready acceptance criteria. The live Jira board was not available in this workspace, so these rows must be matched to existing issues or added to Jira during class. Do not mark a Jira issue Done until its evidence is complete.

| Ticket | Scope and acceptance criteria | Repository evidence | Jira status to use |
| --- | --- | --- | --- |
| S3 M1 01 Model loading | Load one trusted NFL, MLB, and EPL artifact; verify checksum and metadata; reject missing or ambiguous deployments; cache loaded models. | `backend/app/services/model_registry.py`; model registry tests; commit `3d392ce` | Code complete; PR evidence pending |
| S3 M1 02 Prediction service and endpoint | Accept a selected match ID; identify its sport; route through the correct model; expose `POST /predictions`. | Prediction route, schema, and service; commit `3a47b96` | Code complete; PR evidence pending |
| S3 M1 03 Team and history lookup | Query the selected matchup and only final games before its start time; calculate win rate, scoring average, and average allowed. | `MatchHistoryRepository`; automated history tests | Code complete; PR evidence pending |
| S3 M1 04 Validation and error handling | Reject missing, invalid, and extra request fields; return controlled 404, 422, and 503 responses. | Prediction API integration tests | Code complete; PR evidence pending |
| S3 M1 05 Standard response and probabilities | Return the same schema for NFL, MLB, and EPL with home-win and not-home-win probabilities, confidence, model version, and history counts. | Prediction response schemas and parameterized sport tests | Code complete; PR evidence pending |
| S3 M1 06 Backend integration tests and CI | Cover successful and negative paths; run the full Python suite and frontend lint/build on every PR to main. | 136 local tests; updated `.github/workflows/ci.yml` | Local complete; hosted CI pending |
| S3 M1 07 API and frontend integration | Document the API; let the match-details page request and display prediction results, errors, confidence, and history counts. | Backend README; frontend prediction service and panel | Code complete; manual browser test pending |
| S3 M1 08 Sprint artifacts | Complete the final test plan, manual results workbook, PR links, review/approval link, CI link, Jira links, and work-day evidence. | Files under `docs/sprint3`; combined PR to be opened in class | In progress |

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

- Confirm the live Jira board URL and exact issue keys.
- Link the combined Sprint 3 pull request to each applicable issue.
- Obtain a teammate review and approval.
- Wait for both GitHub Actions jobs to pass, then merge through the PR.
- Run and record the live PostgreSQL/model/browser manual cases.
- Demonstrate five distinct real work dates. Current Git evidence shows Member 1 Sprint 3 activity on 8 October 2026 and 15 October 2026 only.
