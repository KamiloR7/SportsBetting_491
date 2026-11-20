# SCRUM-209 — UI scope checklist for feature freeze

**Status:** Proposed scope based on the current frontend and the sprint handoff. The group still needs to confirm the freeze decisions below; this checklist does not claim that the group has approved them.

**Decision rule:** Keep the UI work needed to demonstrate the agreed core flow. Defer optional additions until the group records agreement, an owner, and acceptance criteria. This avoids adding unreviewed scope during release preparation.

## Proposed retained scope

| Keep for the release demo | Evidence in this checkout | Release acceptance |
| --- | --- | --- |
| Browse fixtures by sport, status, team search, and date | `frontend/src/pages/DashBoard.jsx` | Filters update the visible match list; an unmatched selection gives a clear empty state. |
| Open a fixture and show its details, team history, and available prediction | `frontend/src/pages/MatchDetails.jsx` | Known fixture loads its details; missing history is shown as unavailable instead of fabricated. |
| Explain model results and their evaluation limits | `frontend/src/pages/ModelInsightsPage.jsx`; `docs/ml-planning/ml_release_readiness_checklist.md` | The demo distinguishes the reported evaluation from live performance and shows its sample context. |
| Show recent locally saved predictions | `frontend/src/pages/DashBoard.jsx`; `frontend/src/services/predictionHistory.js` | A generated forecast can be found again in the browser history. SCRUM-210 owns accurate class labels and probability display. |
| Present responsive navigation and usable match/detail pages | `frontend/src/App.css`; page styles in `frontend/src` | Main demo flow remains usable at desktop and narrow mobile widths. SCRUM-215 owns the remaining keyboard and mobile polish. |
| Support account sign-in and the virtual betting flow where the integration environment is ready | `frontend/src/pages/Login.jsx`; `frontend/src/components/BetSlip.jsx`; `docs/sprint5-integration-handoff.md` | Show a real accepted response and updated wallet state in the configured integration environment; otherwise mark the step as blocked and use only labeled test evidence. |

## Defer unless the group explicitly agrees

| Optional item | Current basis | Decision needed before implementation |
| --- | --- | --- |
| Prediction cards on every sport-list row | Not implemented; the integration handoff explicitly calls this out. | Agree that list-level forecasts materially improve the release demo and identify the API contract, loading cost, owner, and acceptance criteria. |
| Additional league/status filters or alternate board modes | The existing board already has sport, status, team, and date controls. | Identify a demonstrated user need that the current controls do not cover. |
| New charts, animations, or dashboard visualizations | Existing insights page covers the agreed model explanation. | Specify the question the new visual answers and what release evidence will validate it. |
| Expanding historical replay or adding new model choices to the UI | Current replay and evaluation limitations are documented. | Confirm backend availability, valid-data requirements, and a separate acceptance test. |

## Backend and integration boundaries

- The UI should call the existing same-origin API and present backend responses without inventing fixture, prediction, market, or wallet data. See `backend/docs/backend_integration_readiness.md` and `docs/sprint5-integration-handoff.md`.
- A prediction is explanatory output; it does not settle a bet. Betting availability and final outcomes come from the backend.
- An empty sport/date window is a valid state. Do not promise upcoming fixtures for a sport when the provider has none.
- Browser prediction history is local to the browser. It is not private server-side account history.
- Existing test evidence does not by itself prove the browser/PostgreSQL integration flow. Record that limitation in the demo until individually captured integration evidence is available.

## Freeze sign-off

Use the table during the group review. Mark a decision only after the group discusses it; attach the meeting note or review link so the decision is traceable.

| Decision | Group decision / rationale | Owner and date |
| --- | --- | --- |
| Retain the core demo scope above | Pending group review | Pending |
| Defer optional items unless separately approved | Pending group review | Pending |
| Confirm backend and evidence limits above in the demo script | Pending group review | Pending |

## Release review checklist

- [ ] Group confirms the retained scope and records any changes.
- [ ] Every retained flow has an owner and a demonstrable acceptance step.
- [ ] Deferred work stays out of the release branch unless an explicit decision adds it.
- [ ] SCRUM-210 prediction-history acceptance is reviewed against known fixtures.
- [ ] SCRUM-215 keyboard and mobile polish is reviewed at narrow and desktop widths.
- [ ] Integration-only claims have individually captured evidence; otherwise the limitation remains explicit.

**Source review:** Jira SCRUM-209 asks for a UI scope checklist and warns against developing optional features without agreement. This draft is grounded in the current frontend and the existing Sprint 5 integration handoff. It makes the scope and unresolved approvals visible without implying decisions the group has not yet made.
