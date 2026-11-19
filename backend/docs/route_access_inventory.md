# API Route Access Inventory

**Review date:** 2026-11-19  
**Scope:** Routes registered by `backend/app/main.py` and its included routers.  
**Current disposition:** All API routes are public in the prototype. The backend does not implement login, sessions, tokens, or protected routes. A frontend login screen is not an access control boundary.

| Method and route | Access | Rationale and limits |
| --- | --- | --- |
| `GET /health` | Public | Reports service health and data mode; contains no user-specific data. |
| `GET /sports` | Public | Returns the supported sport catalog. |
| `GET /leagues` | Public | Returns the supported league catalog. |
| `GET /teams` | Public | Returns the supported team catalog. |
| `POST /auth/register` | Public | Creates a new account; registration must be open so a user can create an account. It hashes the submitted password and does not return the hash. It does not create a login session. |
| `GET /matches` | Public | Returns match schedule/results with optional league and status filters; no private account data is returned. |
| `GET /matches/history` | Public | Returns completed match history; no user-specific history is returned. |
| `GET /matches/{match_id}` | Public | Returns a single public match record. |
| `POST /predictions` | Public | Returns a prediction for a public match. The current service has no account-specific prediction data or user identity. |
| `POST /predictions/matches/{match_id}` | Public | Returns a prediction for a public scheduled match. The current service has no account-specific prediction data or user identity. |

## Verification

`backend/tests/test_app_integration.py::TestBackendIntegration.test_route_access_inventory_matches_public_api` compares the documented public route set to the generated OpenAPI operations and fails if route-level or global authentication security is introduced without updating this inventory.

This is a source-level inventory, not a claim that the API currently authenticates users. No route is classified as protected because no server-side authentication mechanism exists. Do not treat the frontend prototype as a way to secure access. Before adding private account, wager, or user-owned data, implement and test server-side authentication and authorization first, then classify those routes as protected here.

## Prototype login evidence

The `/login` form is a UI placeholder. Submitting it must not log or transmit credentials, create a session, navigate as if authentication succeeded, or reveal protected data. The dashboard and current API are public. The form clears the password and displays that sign-in is unavailable. Browser-console and live API checks with synthetic credentials, a deployed environment review, and a hosted CI link remain to be recorded before this assessment can be marked fully verified.
