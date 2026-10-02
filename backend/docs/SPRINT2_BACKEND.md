# Sprint 2 Backend / Database

## Overview

Sprint 2 extends the Sports Match Prediction backend with user registration, match retrieval, historical match retrieval, request validation, and automated backend testing.

The backend uses FastAPI, SQLAlchemy, and PostgreSQL.

## API Endpoints

Existing project endpoints:

- `GET /health`
- `GET /sports`
- `GET /leagues`
- `GET /teams`

Sprint 2 endpoints:

- `POST /auth/register`
- `GET /matches`
- `GET /matches/{match_id}`
- `GET /matches/history`

## User Registration

`POST /auth/register` creates a new user.

Registration includes:

- Email validation
- Username validation
- Password length validation
- Duplicate email checking
- Duplicate username checking
- bcrypt password hashing

Passwords and password hashes are not returned by the API.

## Match APIs

`GET /matches` returns available match data and supports optional league and status filtering.

`GET /matches/{match_id}` returns an individual match. A missing match returns a 404 response.

`GET /matches/history` returns completed historical matches and supports league filtering and a configurable result limit.

## Validation and Testing

Sprint 2 adds validation for registration inputs and match API parameters.

Automated tests cover:

- Valid and invalid registration input
- Password hashing
- Duplicate registration handling
- Match retrieval
- Historical match retrieval
- Missing match handling
- Backend route integration

Run the backend tests with:

```bash
python -m pytest tests -v
```

## Database Setup

Database configuration is loaded from environment variables.

See:

- `.env.example`
- `DATABASE_SETUP_README.md`

The users table includes a `password_hash` field for securely storing hashed passwords.

Local database credentials should not be committed to Git.

## Known Limitation

Sprint 2 establishes the registration and authentication foundation. Full login, session, or token-based authentication can be added in a later backend sprint.

Live registration also requires a correctly configured local PostgreSQL database.

## Handoff

The backend now provides user registration, sport/team data access, match retrieval, historical match retrieval, validation, and automated testing.

Future work can build on these APIs for frontend integration, prediction requests, and expanded authentication.