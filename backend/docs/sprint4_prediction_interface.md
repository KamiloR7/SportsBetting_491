# Sprint 4 prepared-feature prediction interface

## Scope and dependencies

This separate contribution is on `member3/sprint4-prediction-interface` in
`/private/tmp/SportsBetting_491-sprint4-interface`, based on training commit
`e9b7cd5`. At inspection, latest main is `7b31053` and PRs
[#43](https://github.com/KamiloR7/SportsBetting_491/pull/43) (chronological data),
[#44](https://github.com/KamiloR7/SportsBetting_491/pull/44) (features),
[#45](https://github.com/KamiloR7/SportsBetting_491/pull/45) (baselines), and
[#46](https://github.com/KamiloR7/SportsBetting_491/pull/46) (training) are open
and unmerged. A later stacked PR should target `member3/sprint4-ml-training`.
No Jira key, merge, main modification or rewrite is part of this work.

Supported leagues and public probability class order:

| Sport | Class order |
| --- | --- |
| NFL | home_win, away_win |
| MLB | home_win, away_win |
| EPL | home_win, draw, away_win |

NFL probabilities follow the trained binary contract, conditional on a decisive
outcome; ties remain historical information and are excluded from classifier
targets. EPL draw classification is native to the trained three-class model,
not a split of an inferred binary away-win probability.

## Integration decision

Existing `POST /predictions` and `POST /predictions/matches/{match_id}` use legacy
six-feature models and different response schemas. They remain unchanged.
Their database repositories do resolve match IDs, but do not produce the full
historical sport feature schema or trustworthy result-availability evidence.
Adapting those records silently would violate the new model contract.

Add `POST /predictions/prepared` through a separate router, schema and service;
main only imports/registers the new router. It has no database dependency and
accepts prepared features. An ID-only request is invalid, not a database lookup.
The returned match ID is the caller's prepared-record identifier, not proof that
an internal database match was resolved. There is no new SQL resolver, inferred
availability time, or replacement of legacy inference.

This endpoint is suitable for explicitly configured trusted-local development
artifacts. By default no model is configured and valid requests return 503.
No test model, synthetic model, untrained model, automatic file discovery, or
baseline fallback is installed into the application.

## Service API and explicit model configuration

`PreparedPredictionService.predict_prepared(request)` accepts either a mapping
or a `PreparedPredictionRequest`. Even model instances are revalidated to detect
unvalidated construction/mutation. It returns a typed `PreparedPredictionResponse`
or raises `PredictionInterfaceError` with `code`, `message`, `status_code`, and
safe structured `detail`.

`TrustedHistoricalModelRegistry` accepts an operator-owned mapping from uppercase
sport to `TrustedModelSpec(path, model_version)`. Both the path and exact version
are selected outside the request. Loading requires explicit `trusted_local=True`;
the service never accepts a client artifact path. The selected artifact is loaded
using `load_historical_model`, including schema/configuration/software-version,
checksum and fitted-state checks. Loaded models are cached per selected sport;
change registry/service configuration explicitly to deploy a different version.
There is no implicit latest-version selection or hot reload.

Example Backend development setup (only after verifying the artifact is trusted):

```python
from pathlib import Path
from datetime import timedelta
from app.main import app
from app.services.prepared_prediction_service import (
    PreparedPredictionService, TrustedHistoricalModelRegistry, TrustedModelSpec,
    get_prepared_prediction_service,
)

registry = TrustedHistoricalModelRegistry(
    {"EPL": TrustedModelSpec(Path(approved_local_path), approved_model_version)},
    trusted_local=True,
)
service = PreparedPredictionService(registry, max_source_age=timedelta(hours=24))
app.dependency_overrides[get_prepared_prediction_service] = lambda: service
```

`approved_local_path` and `approved_model_version` must come from an operator's
verified local training output, not a request or uploaded file. The default
cached dependency contains an empty registry. This example does not install or
approve a production model. Pickle can execute code: checksums and flags do not
establish authenticity or make untrusted files safe. Follow the training
artifact trust requirements; never enable untrusted model uploads.

## Prepared request contract

All fields are required except `source_observed_at`. Extra fields are forbidden.

| Field | Contract |
| --- | --- |
| `match_id` | Nonblank string prepared-record identifier, normally the feature pipeline's `game_id` |
| `sport` | Exact NFL, MLB or EPL identifier |
| `start_time` | Genuine timezone-aware kickoff |
| `feature_as_of` | Aware availability cutoff, strictly before kickoff and no later than prediction processing time |
| `feature_schema_version` | Exact `historical_sport_features_v1` |
| `feature_columns` | Exact ordered `feature_columns(sport)` list |
| `features` | Mapping with exactly that predictor key set, no metadata, outcome or extra values |
| `model_version` | Exact operator-selected model version |
| `source_results` | Explicit list of all result evidence used in features, including indirect opponent-strength history |
| `source_observed_at` | Optional reliable provider/source snapshot observation time; required when an age policy is configured |

Each `source_results` entry has `source_game_id`, `start_time`, and
`result_available_at`. Identities must be nonblank, unique in the supplied source
scope, and exclude the target identifier. Source kickoff must be on a prior UTC
day, result availability strictly after that kickoff, and availability no later
than the feature cutoff. The evidence list must contain at least as many unique
results as either team's supplied season match count. Both teams may share
historical games, so the required lower bound is their maximum, not their sum.
Cold-start count-zero requests can explicitly supply an empty evidence list.

This is a consistency/lower-bound check, **not proof of completeness** or a
reconstruction of numeric features. Backend must obtain prepared statistics and
all supporting evidence from verified canonical histories and the historical
feature pipeline. Arbitrary clients can assert false numbers/timestamps; this
service cannot establish provenance truth, source identity or archive
completeness from a prepared numeric vector. Real-data control acceptance
requires external evidence. No database lookup is claimed for `match_id`.

Predictor values are strict numeric values or missing values; strings and
booleans reject. Python `NaN` and JSON `null` represent legitimate unavailable
rates/means and are passed as NaN to the trained imputer. Standard JSON should
use `null`, not non-standard NaN literals. Counts must be finite nonnegative
integers; rates are bounded, scoring averages nonnegative, and signed margins
are valid. Infinite values reject. Season counts must reconcile, recent counts
must equal min(5/10, season matches), venue counts cannot exceed season counts,
and available scoring averages must reconcile with their margin. Missing
means are not filled by the service; only the fitted training imputer fills them.
Declared feature order is checked exactly; dictionary insertion order is irrelevant.

A minimal assembly example avoids hardcoding a sport's dozens of predictor names:

```python
from app.ml.features.historical_sport_features import SCHEMA_VERSION, feature_columns

request = {
    "match_id": prepared_game_id,
    "sport": "EPL",
    "start_time": verified_kickoff_iso,
    "feature_as_of": verified_feature_cutoff_iso,
    "feature_schema_version": SCHEMA_VERSION,
    "feature_columns": feature_columns("EPL"),
    "features": verified_feature_values,  # only predictors; use null for JSON missing means
    "model_version": approved_model_version,
    "source_results": verified_result_timestamp_records,
    "source_observed_at": verified_source_observation_iso,
}
response = service.predict_prepared(request)
```

These variables must come from genuine prepared inputs; the example is not a
generated dataset or a statement that a real model is available.

## Cutoffs and freshness

All timestamp fields accept aware datetimes or ISO strings with timezone; naive
values, raw epoch numbers and missing required timestamps reject. The service
checks features, evidence ordering and processing-clock cutoff before loading a
model. It then checks the model's training cutoff and latest training label
availability before inference, reusing the historical baseline guard. The
trained inference method repeats its own schema/cutoff/integrity checks and
probability validation. Invalid inputs do not reach `predict_proba`.

If provided, source observation cannot follow the feature cutoff or precede any
claimed included result availability. Optional `max_source_age` is a positive
operator-configured timedelta. When configured, observation time is mandatory
and `(feature_as_of - source_observed_at) <= max_source_age`; equality is allowed.
A response then reports `within_configured_age`. Without the policy, status is
`not_evaluated`: freshness is not invented from kickoff or a guessed source time.
These statuses describe checks of supplied timestamps, not independent source
authenticity verification or formal SOC 2 acceptance.

Prepared historical replay is supported: the cutoff can be historical while
`generated_at` records actual processing time. This is not a guarantee of live
scheduled-match freshness. A future source snapshot/feature cutoff relative to
the processing clock rejects. There is no universal hardcoded freshness limit.

## Standard response

```text
match_id, sport, predicted_outcome,
probabilities {home_win, away_win; plus draw for EPL},
class_order, model_identifier, model_version, feature_schema_version,
generated_at, prediction_cutoff,
prediction_method="historical_logistic_regression",
source="trusted_local_development_artifact",
freshness_status="not_evaluated" or "within_configured_age"
```

Model identifier is `historical_logistic_regression_v1`. Class order is stable
as listed above. Probabilities must be finite, in [0,1], have exactly the sport's
classes, and sum within absolute 0.000001 of one. The predicted outcome is the
argmax; ties use stable class order. The requested match/sport/model identity is
checked against the model output. The response is validated before returning;
malformed predictions yield a controlled error, not a fabricated substitute.
Processing time can differ across repeated calls, while numerical inference is
deterministic for unchanged model/features. Tests inject a fixed clock to compare
complete responses without claiming production timestamp determinism.

## Structured errors

All new route failures use `detail.code` and `detail.message`. Request validation
also includes field locations/types/messages, omitting submitted values. The
custom route handler is scoped to this router; legacy error contracts are unchanged.

| HTTP | Representative codes |
| --- | --- |
| 422 | invalid_request, invalid_features, invalid_features_or_cutoff, invalid_feature_consistency |
| 422 | invalid_provenance, missing_provenance, historical_cutoff_violation, training_cutoff_violation, future_feature_cutoff |
| 422 | freshness_unavailable, stale_source, invalid_source_timestamp |
| 409 | feature_schema_mismatch, model_version_mismatch |
| 503 | model_unavailable, prediction_unavailable |
| 502 | prediction_failed |

Unsupported sports and ID-only requests are invalid requests. Missing/incompatible
artifacts and absent trust configuration return model_unavailable. Errors do not
expose local artifact paths, payloads, or internal loader exception messages.
No silent baseline fallback or production model is configured.

## Limitations and assessment boundary

No verified real historical data, availability provenance or production-trained
artifacts exist in this checkout. Models in automated tests are controlled
synthetic engineering fixtures and remain in temporary directories. They are
explicitly labeled as trusted-local development output and are not registered
in the real default application. No accuracy, production readiness, live model
coverage, or formal SOC 2 P1 control acceptance is claimed.

A future match-ID adapter requires source/season lineage, rich feature generation
and reliable result-availability evidence from Backend. Existing database match
history lacks that complete contract. This contribution does not alter database
schema, authentication, deployment, legacy routes/models, or the earlier ML
contributions. Real-data acceptance, real PostgreSQL execution and hosted CI
remain separate verification work.

## Local verification

- **49 new interface tests passed** for prepared requests, all supported sports,
  native EPL draws, probability contracts, model/schema/version errors, missing
  artifacts, declared ordering, missing-history NaN/null handling, cutoff and
  provenance errors, freshness policy boundaries, invalid inputs before loading
  or execution, default model-unavailable behavior, and legacy route coexistence.
- The focused new-service/legacy prediction subset passed before the final
  mapping-order case was added; the final full run includes that additional case.
- Full regression under the existing SCRUM-203 network/PostgreSQL guard:
  **714 passed, 0 failed, 4 skipped**. The four PostgreSQL integration tests need
  a separately authorized disposable database and were not executed.
- Python compilation passed for backend/app, backend/tests, backend/src and src.
- Whitespace/final-newline checks passed for the five new files and the two-line
  main router registration change.
- No configured backend lint/type-check command exists. Frontend ESLint is
  unrelated to this Python-only integration.

Evidence: `/private/tmp/sprint4-interface-focused.xml` and
`/private/tmp/sprint4-interface-regression.xml` (local artifacts, not hosted CI).
Tests use the existing isolated coverage-enabled Python environment; no shared
packages or tracked requirements were changed. No network or PostgreSQL access
was used by the guarded regression run. The route-registration test uses dummy
backend environment values solely to construct the existing app, not a database.

This isolated contribution targets `member3/sprint4-ml-training` as a stacked
PR until its prerequisites merge. Only the new service/schema/router, their
tests/docs, and main's additive registration differ from the training base.
Merging, rewriting prerequisite commits, and changing other worktrees/stashes
are outside this contribution's scope. The implementation is ready for peer review as a
separate dependent contribution; real-data acceptance, match-ID adapter support,
production deployment and formal SOC 2 P1 assessment remain future work.
