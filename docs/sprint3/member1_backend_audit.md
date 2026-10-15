# Member 1 Sprint 3 Backend Audit

Audit date: 2026-10-15

Original Sprint 3 workflow:

1. Receive a selected matchup.
2. Validate the request and identify NFL, MLB, or EPL.
3. Retrieve team and historical-game information.
4. Build model features and load the correct trained model.
5. Generate a prediction with probability/confidence values.
6. Return a standardized response to the frontend.

## Baseline audit

| Requirement | Baseline repository evidence | Initial status |
| --- | --- | --- |
| Model loading | `backend/app/ml/predict_multisport.py` verified a single artifact checksum, but no backend registry mapped or cached NFL/MLB/EPL artifacts. | Incomplete |
| Prediction service | No backend service orchestrated lookup, feature construction, and prediction. | Missing |
| NFL/MLB/EPL paths | Sprint 2 training covered all three sports, but no API prediction path selected among them. | Incomplete |
| Team/history lookup | Read-only match history endpoint existed; no prediction feature lookup service existed. | Incomplete |
| Input validation | Existing match endpoints validated query parameters; no prediction request schema existed. | Missing |
| Standardized response | The ML utility returned a binary DataFrame; no API response schema existed. | Missing |
| Probability/confidence | Binary model probabilities existed below the API layer only. | Incomplete |
| Backend integration tests | Existing route and ML tests did not exercise a prediction endpoint. | Missing |
| API documentation | Backend README said prediction functionality was planned for a future sprint. | Missing |
| Frontend-to-backend prediction flow | Frontend called match endpoints but had no prediction service call. | Missing |
| PR/review/CI evidence | CI runs on pull requests to `main`; Sprint 3 prediction PR evidence did not yet exist. | Missing |
| Jira alignment | Requires verification against the live Jira board. | Not verifiable locally |
| Final test plan | No Sprint 3 Member 1 backend test plan was present. | Missing |
| Manual test evidence | No Sprint 3 prediction API results were present. | Missing |
| Five or more work days | Must be demonstrated by truthful GitHub, Jira, and document history. | Not yet established |

## Item 1: model loading

Implemented `ModelRegistry` to:

- support NFL, MLB, and EPL;
- discover exactly one immutable Sprint 2 artifact per sport;
- require explicit selection when multiple versions exist;
- reuse the existing SHA-256 verification before unpickling;
- validate sport, feature schema, and model classes from metadata; and
- cache each verified model for reuse.

### Automated evidence

Command:

```text
PYTHONPATH=backend python -m pytest -q backend/tests/test_model_registry.py backend/tests/test_multisport_completion.py
```

Result on 2026-10-15:

```text
35 passed in 1.55s
```

Full regression command:

```text
PYTHONPATH=backend python -m pytest -q
```

Result on 2026-10-15:

```text
126 passed in 5.74s
```

Status: implemented and locally verified; PR review, CI, approval, and merge remain required before this item is complete evidence.
