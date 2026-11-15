# Sprint 1 to Sprint 5 database evolution

Verified November 13, 2026, using Git history, source definitions and read-only PostgreSQL catalogs. The physical schema export is authoritative for the current local database; SQL source alone is not evidence of when an object was applied.

## Historical baseline

The earliest Git revision containing `backend/app/database/sports_prediction_schema.sql` is **`1202e94`**, committed September 15, 2026, 13:53:17 PDT, “Added PostgreSQL database, database schema and documentation. Readme.md is also available for teammate handoff”. The file identifies itself as the Sprint 1 team-review schema. `sprint1_schema_reference.sql` is the exact file extracted from that revision, without retroactive additions.

Its **13 tables** are `sports`, `leagues`, `seasons`, `teams`, `season_teams`, `matches`, `model_versions`, `match_predictions`, `users`, `user_predictions`, `data_sources`, `external_mappings`, and `ingestion_runs`. All 13 names are present in the live database. Prediction, user and ingestion tables therefore originated in Sprint 1, even when their runtime functionality was implemented later.

The original `users` table had no password-hash column. The current file at the same path is not an unchanged historical Sprint 1 artifact: commit **`5a9d0a0`**, October 1, 2026, 17:40:06 PDT, “Implement user registration and authentication foundation”, added `password_hash VARCHAR(255) NOT NULL`. Git shows that as the only change to this SQL file since its initial addition.

## Timeline: definition versus database application

| Stage | Version-controlled definition evidence | Verified local database effect |
|---|---|---|
| Sprint 1 baseline | `1202e94`: 13 tables, no password hash | All 13 original table structures remain present. Exact original installation date is not recoverable from Git alone. |
| Authentication foundation | `5a9d0a0`: password-hash column added to SQL source | The local DB still lacked that column before Sprint 5 verification. A source change did not imply an applied migration. |
| Sprint 4 authentication assessment | `2a4223e`, November 5, 2026, 12:28:19 PST: adds `app/database/auth_tables.py` defining four auth tables | Previous setup evidence confirms those tables were absent locally before Sprint 5 setup. |
| Sprint 5 setup | Existing four auth definitions reused; five betting table definitions added in Sprint 5 feature-branch work | Nine new tables created in local `sports_betting`; associated constraints, indexes and sequences created. |
| Approved Sprint 5 correction | Existing auth code required the previously defined password-hash column | Added `users.password_hash VARCHAR(255) NOT NULL` after empty-table, column-absence and backup checks, with explicit approval. |

Thus **9 tables were added to this local database during Sprint 5**, but only **5 table definitions are new to the Sprint 5 implementation**. The other **4 definitions originated in Sprint 4**. Do not describe all nine as first designed in Sprint 5.

## Tables added during local Sprint 5 setup

| Table | Definition origin | New connection / role |
|---|---|---|
| `auth_sessions` | Sprint 4 | Required `user_id` FK; persistent session digest, CSRF material, expiry; user deletion cascades. |
| `auth_csrf_challenges` | Sprint 4 | Pre-login challenge state, no user FK. |
| `auth_login_attempts` | Sprint 4 | Account-derived digest keys and throttle history, no user FK. |
| `auth_assessment_records` | Sprint 4 | Synthetic assessment ownership via required user FK; not betting history. |
| `virtual_wallets` | Sprint 5 | `user_id` is both PK and FK: at most one wallet per user. |
| `demo_markets` | Sprint 5 | Required unique `match_id` FK: at most one market per match. |
| `demo_outcomes` | Sprint 5 | Required market FK; selection/odds checks; unique market/selection pair. |
| `virtual_bets` | Sprint 5 | Required user, match and outcome FKs; accepted odds snapshot, stake/payout, status and per-user retry key. |
| `virtual_wallet_transactions` | Sprint 5 | Required user FK; signed point amounts and unique per-user ledger reference. |

The nine-table preview is a CREATE-only preview. It does **not** include the separately approved `ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NOT NULL`. It must not be presented as a complete migration history.

## Existing table modification

The only live column addition relative to the historical 13-table baseline is **`users.password_hash VARCHAR(255) NOT NULL`**, with no default. It is physically the last column in the live table because it was added later; current source SQL places it before `is_active`. Column ordering is cosmetic for named-column operations but is an observable export difference. The documentation contains only the column definition, no stored hashes.

No other original columns were found missing or added. Original type, nullability, default, primary-key, foreign-key, unique-key and named-check definitions were compared to the catalog. All eight explicit Sprint 1 indexes remain present. PostgreSQL renders types and CHECK expressions differently from source (`BIGSERIAL` becomes `bigint` plus an owned sequence/default; `FLOAT` becomes `double precision`; `IN` checks may become `ANY(ARRAY...)`; `BETWEEN` becomes bounds comparisons). These are representational differences rather than missing constraints. All original timestamp columns were verified as `TIMESTAMP WITH TIME ZONE`.

## Preserved and extended relationships

Sports retain one-to-many relationships to leagues and teams. Leagues connect to seasons; `season_teams` bridges seasons and teams. Matches reference leagues, optional seasons and two teams independently. There is no direct teams-to-leagues FK. FKs alone do not require that a match's team sport agrees with its league or that its season belongs to its league.

Model predictions continue to reference match/model/team IDs. User predictions retain their user/match/team references and are separate from bets. `external_mappings.entity_id` remains a polymorphic identifier without a physical entity FK.

Sprint 5 attaches markets to existing match IDs and bets to users, matches and outcomes. Wallets and ledger records attach to users. Ledger reference strings do not create a bet FK. Session/challenge/throttle data remains separate from sports and model inference.

## Application-enforced rules and gaps

- Virtual points are integers with no cash value. A new wallet's 1,000-point starting credit is application logic; the schema does not default balance to 1,000.
- Wallet CHECK prevents negative balances. Stake deduction, bet insertion and ledger entry are one application transaction with PostgreSQL locks.
- Unique user/request keys prevent duplicate bet identity; application logic additionally rejects reuse with different payloads. Ledger reference uniqueness supports refill/payout retry protection.
- Winning credit is the stored `floor(stake × accepted decimal odds)`, including the stake. Loss credits nothing. Voids refund the stake. NFL/MLB ties void two-way markets; EPL draws settle draw selections. These are service rules, not triggers or stored functions.
- DB FKs do not enforce outcome-to-bet-match consistency across the market join, draw eligibility by league, balance-to-ledger equality, or settlement transitions. The bet service handles applicable validation and transactions. `accepted_odds` itself has no standalone DB range CHECK, although stored outcome odds are checked.
- No user-defined views, materialized views, functions/procedures or triggers were found. `updated_at` insertion defaults do not automatically update timestamps.
- Synthetic fixture source is known from the seed procedure and verification report. The match schema has no dedicated synthetic/demo provenance flag, and `demo_markets` has no persisted odds-source column; the API supplies a synthetic-demo label.
- There is no committed, versioned migration ledger establishing every local application event. Sprint 5 implementation is supplied on the feature branch. Git dates establish source introduction, while prior setup reports establish local application.

No schema discrepancies were corrected during this documentation task. Further constraints, indexes, migrations, provenance fields or features require separate implementation work.
