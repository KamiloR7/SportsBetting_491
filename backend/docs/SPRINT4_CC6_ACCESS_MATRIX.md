# Sprint 4 — SOC 2 CC6.1 Backend API Access Matrix

**Project:** Vigor — Sports Match Prediction Application  
**Sprint:** Sprint 4  
**Jira Task:** SCRUM-186  
**Branch:** feature/sprint4-soc2-authentication  
**Review Date:** November 5, 2026  
**Review Status:** Complete

## 1. Purpose

This document identifies which backend API endpoints are public, which require authentication, and which require additional security controls.

The review supports SOC 2 CC6.1 — Logical Access Security.

The access classifications are based on the current FastAPI implementation and the authentication functionality developed during Sprint 4.

## 2. Backend API Access Matrix

| HTTP Method | Endpoint | Access Classification | Authentication Required | Purpose |
|---|---|---|---|---|
| POST | /auth/register | Public | No | Register a new user account |
| POST | /auth/login | Public | No | Verify credentials and create a session |
| POST | /auth/logout | Protected + CSRF | Yes | Revoke an authenticated session |
| GET | /auth/me | Protected | Yes | Retrieve the authenticated user's information |
| GET | /auth/csrf | Protected | Yes | Generate a session-bound CSRF token |
| GET | /health | Public | No | Check API availability |
| GET | /sports | Public | No | Retrieve available sports |
| GET | /leagues | Public | No | Retrieve available leagues |
| GET | /teams | Public | No | Retrieve available teams |
| GET | /matches | Public | No | Retrieve match information |
| GET | /matches/history | Public | No | Retrieve public historical match results |
| GET | /matches/{match_id} | Public | No | Retrieve a specific match |
| POST | /predictions | Public | No | Generate a machine-learning match prediction |
| POST | /predictions/matches/{match_id} | Public | No | Calculate and return a match prediction |
| GET | /assessment/predictions/{prediction_id} | Authenticated + ownership | YES | Only the record owner may retrieve it |
| PATCH | /assessment/predictions/{prediction_id} | Authenticated + ownership + CSRF | YES | Only the owner may modify it |

## 3. Prediction API Access Review

**Files reviewed:**
- app/routes/predictions.py
- app/services/prediction_service.py

### POST /predictions

The endpoint calls PredictionService.predict(), which retrieves match context, runs the prediction model, calculates probabilities, and returns a PredictionResponse.

The inspected implementation does not create or modify user-owned prediction records.

**Classification: Public**

### POST /predictions/matches/{match_id}

The endpoint retrieves match information and historical results, calculates prediction probabilities, and returns a PredictionOut response.

The inspected implementation does not perform database writes to user_predictions or modify user account information.

**Classification: Public**

### Security Decision

Both prediction-generation endpoints are public because their current purpose is to calculate match outcomes rather than modify account-owned resources.

If future functionality allows users to save, edit, or delete their own predictions, those operations must enforce authentication and resource ownership.

## 4. Authentication and Session Controls

The Sprint 4 authentication prototype includes:

- bcrypt password verification.
- Session creation after successful login.
- A 30-minute server-side session lifetime.
- Session invalidation during logout.
- HttpOnly, Secure, and SameSite=Lax session cookie attributes.
- Authentication enforcement for /auth/me.
- Session-bound CSRF token generation.
- CSRF validation for /auth/logout.
- Generic invalid-credential error messages.

### Sprint 4 Security Implementation Limitations

The authentication prototype includes session-based access control, CSRF validation, bcrypt password verification, and login throttling.

**Verified locally:** Authentication and security tests using synthetic users and mocked SQLAlchemy database access.

**Known limitations:**
- Session storage is process-local and is not shared between backend workers.
- Login throttling uses process-local state and requires shared storage for multi-instance deployment.
- Current CSRF enforcement is implemented for authenticated logout. Future cookie-authenticated write endpoints require equivalent protection.
- PostgreSQL integration and CI security verification remain pending.
- Production deployment requires HTTPS, appropriate CORS configuration, and a durable session-storage strategy.

These limitations do not prevent the Sprint 4 prototype from being tested, but they must not be represented as completed production-security controls.

## 5. Future Resource Ownership Requirements

The database schema contains a user_predictions table associated with users through user_id.

Although the prediction-generation endpoints are public, future operations that access user-owned prediction records must enforce authorization.

Required behavior for such operations:

- Anonymous users must be denied access.
- Authenticated users may access only resources they are authorized to access.
- Cross-account read and write requests must be denied.
- Unauthorized requests must not modify protected records.

Resource ownership implementation and testing are tracked under SCRUM-189 and SCRUM-206.

## 6. Sprint 4 Testing Evidence

Local automated tests have verified:

- Successful login.
- Incorrect-password rejection.
- Anonymous access rejection.
- Authenticated access to /auth/me.
- Logout and subsequent session rejection.
- Missing-CSRF-token rejection during logout.
- Correct 30-minute session expiration.

**Latest verified results:**
- Authentication HTTP tests: 6 passed.
- Combined authentication tests: 21 passed, 0 failed.

These tests use synthetic accounts and mocked database access.

PostgreSQL integration tests and final CI verification remain separate requirements.

## 7. Review Conclusion

The existing backend routes have been reviewed and classified according to their current access requirements.

The prediction-generation endpoints were inspected to determine whether they perform user-owned writes.

The Sprint 4 authentication and CSRF routes have been added to the access matrix.

**SCRUM-186 Status: Complete**

Remaining authentication implementation, negative testing, ownership enforcement, PostgreSQL integration, and CI/CD evidence are tracked separately.

## 8. Related Jira Tasks

- SCRUM-186 — Review Backend Routes and Finalize Access Matrix
- SCRUM-187 — Implement Login, Sessions, Logout, and Protected API Access
- SCRUM-188 — CSRF, Secure Cookies, and Login Throttling
- SCRUM-189 — Resource Ownership and Denied-Write Authorization
- SCRUM-204 — Authentication and Session Lifecycle Testing
- SCRUM-205 — Security Denial, CSRF, and Throttling Tests
- SCRUM-206 — Cross-Account and Denied-Write Tests
- SCRUM-207 — API Response and Security Evidence Review