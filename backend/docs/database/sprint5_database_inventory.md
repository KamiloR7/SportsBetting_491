# Sprint 5 verified database inventory

Snapshot: November 13, 2026 (America/Los_Angeles). Local development database `sports_betting`, loopback port 5432. Metadata-only inspection; no application records were read for this documentation.

Verified totals: **22 tables, 138 columns, 26 foreign keys, 77 table constraints, 44 indexes, 17 sequences**. All application tables are in `public`. Constraint counts exclude column-level NOT NULL flags, which appear in the column tables. Index totals include indexes backing primary and unique keys.

The schema-only export is [sprint5_actual_schema.sql](sprint5_actual_schema.sql). Historical reference: [sprint1_schema_reference.sql](sprint1_schema_reference.sql). All betting uses simulated integer virtual points with no monetary value. Demo odds and match fixtures are synthetic, not live bookmaker information.

## Table inventory

| Table | Origin | Purpose |
|---|---|---|
| `sports` | Sprint 1 SQL, commit `1202e94` (2026-09-15) | Sport catalogue; EPL/NFL/MLB are leagues, not sport rows. |
| `leagues` | Sprint 1 SQL, commit `1202e94` (2026-09-15) | Leagues associated with sports; abbreviations identify EPL, NFL and MLB. |
| `seasons` | Sprint 1 SQL, commit `1202e94` (2026-09-15) | Season metadata associated with a league. |
| `teams` | Sprint 1 SQL, commit `1202e94` (2026-09-15) | Teams associated directly with a sport, not directly with a league. |
| `season_teams` | Sprint 1 SQL, commit `1202e94` (2026-09-15) | Many-to-many season/team membership, with conference/division context. |
| `matches` | Sprint 1 SQL, commit `1202e94` (2026-09-15) | Scheduled/completed matchups, team references, times and scores. |
| `match_predictions` | Sprint 1 SQL, commit `1202e94` (2026-09-15) | Stored model prediction schema; table existence does not prove current endpoints write predictions. |
| `model_versions` | Sprint 1 SQL, commit `1202e94` (2026-09-15) | Prediction model metadata and metrics. |
| `user_predictions` | Sprint 1 SQL, commit `1202e94` (2026-09-15) | Per-user match picks; separate from virtual bets and model predictions. |
| `users` | Sprint 1 SQL, commit `1202e94` (2026-09-15) | Persistent accounts; password_hash stores bcrypt output, never plaintext passwords. |
| `data_sources` | Sprint 1 SQL, commit `1202e94` (2026-09-15) | Source catalogue for ingestion. |
| `external_mappings` | Sprint 1 SQL, commit `1202e94` (2026-09-15) | Provider identifiers; entity_id is a polymorphic application reference, not a database FK. |
| `ingestion_runs` | Sprint 1 SQL, commit `1202e94` (2026-09-15) | Ingestion execution metadata. |
| `auth_sessions` | Auth definitions introduced in Sprint 4, commit `2a4223e` (2026-11-05); created in this local DB during Sprint 5 setup | Persistent sessions keyed by digest; user FK and expiry enable lookup/revocation. No token values are included here. |
| `auth_csrf_challenges` | Auth definitions introduced in Sprint 4, commit `2a4223e` (2026-11-05); created in this local DB during Sprint 5 setup | Pre-login challenge digests, CSRF material and expiration; no user FK by design. |
| `auth_login_attempts` | Auth definitions introduced in Sprint 4, commit `2a4223e` (2026-11-05); created in this local DB during Sprint 5 setup | Account-derived digest keys, failure history and temporary login blocking; no user FK so nonexistent accounts can be throttled. |
| `auth_assessment_records` | Auth definitions introduced in Sprint 4, commit `2a4223e` (2026-11-05); created in this local DB during Sprint 5 setup | Synthetic Sprint 4 ownership-assessment records; not bet history or an operational wallet table. |
| `virtual_wallets` | Sprint 5 virtual-betting implementation; Sprint 5 feature-branch files | One virtual-points balance per user; initial 1,000-point credit is application logic, not a SQL default. |
| `demo_markets` | Sprint 5 virtual-betting implementation; Sprint 5 feature-branch files | At most one single-match winner market per match. |
| `virtual_wallet_transactions` | Sprint 5 virtual-betting implementation; Sprint 5 feature-branch files | Signed integer ledger amounts; application reference strings support retry protection. No real currency. |
| `demo_outcomes` | Sprint 5 virtual-betting implementation; Sprint 5 feature-branch files | Stored synthetic decimal odds for home/away and EPL draw selections. |
| `virtual_bets` | Sprint 5 virtual-betting implementation; Sprint 5 feature-branch files | User-owned stake, accepted odds snapshot, potential payout, result status and idempotency key. |

## `sports`

Sport catalogue; EPL/NFL/MLB are leagues, not sport rows.

Origin: Sprint 1 SQL, commit `1202e94` (2026-09-15).

| Column | PostgreSQL type | Nullable | Default / identity | Keys |
|---|---|---|---|---|
| `id` | `BIGINT` | No | `nextval('"public".sports_id_seq'::regclass)` | PK |
| `name` | `VARCHAR(80)` | No | `—` | UNIQUE |
| `slug` | `VARCHAR(80)` | No | `—` | UNIQUE |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Yes | `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | Yes | `now()` | — |

### Constraints

| Name | Kind | Verified PostgreSQL definition | Validated |
|---|---|---|---|
| `sports_name_key` | Unique | `UNIQUE (name)` | True |
| `sports_pkey` | Primary key | `PRIMARY KEY (id)` | True |
| `sports_slug_key` | Unique | `UNIQUE (slug)` | True |

### Indexes

| Index | Definition | Valid / ready |
|---|---|---|
| `sports_name_key` | `CREATE UNIQUE INDEX sports_name_key ON public.sports USING btree (name)` | True / True |
| `sports_pkey` | `CREATE UNIQUE INDEX sports_pkey ON public.sports USING btree (id)` | True / True |
| `sports_slug_key` | `CREATE UNIQUE INDEX sports_slug_key ON public.sports USING btree (slug)` | True / True |

## `leagues`

Leagues associated with sports; abbreviations identify EPL, NFL and MLB.

Origin: Sprint 1 SQL, commit `1202e94` (2026-09-15).

| Column | PostgreSQL type | Nullable | Default / identity | Keys |
|---|---|---|---|---|
| `id` | `BIGINT` | No | `nextval('"public".leagues_id_seq'::regclass)` | PK |
| `sport_id` | `BIGINT` | Yes | `—` | FK → sports.id |
| `name` | `VARCHAR(120)` | No | `—` | — |
| `abbreviation` | `VARCHAR(30)` | Yes | `—` | — |
| `country` | `VARCHAR(80)` | Yes | `—` | — |
| `active` | `BOOLEAN` | Yes | `true` | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Yes | `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | Yes | `now()` | — |

### Constraints

| Name | Kind | Verified PostgreSQL definition | Validated |
|---|---|---|---|
| `leagues_pkey` | Primary key | `PRIMARY KEY (id)` | True |
| `leagues_sport_id_fkey` | Foreign key | `FOREIGN KEY (sport_id) REFERENCES sports(id)` | True |

### Indexes

| Index | Definition | Valid / ready |
|---|---|---|
| `leagues_pkey` | `CREATE UNIQUE INDEX leagues_pkey ON public.leagues USING btree (id)` | True / True |

## `seasons`

Season metadata associated with a league.

Origin: Sprint 1 SQL, commit `1202e94` (2026-09-15).

| Column | PostgreSQL type | Nullable | Default / identity | Keys |
|---|---|---|---|---|
| `id` | `BIGINT` | No | `nextval('"public".seasons_id_seq'::regclass)` | PK |
| `league_id` | `BIGINT` | Yes | `—` | FK → leagues.id |
| `name` | `VARCHAR(60)` | No | `—` | — |
| `start_date` | `DATE` | Yes | `—` | — |
| `end_date` | `DATE` | Yes | `—` | — |
| `is_current` | `BOOLEAN` | Yes | `false` | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Yes | `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | Yes | `now()` | — |

### Constraints

| Name | Kind | Verified PostgreSQL definition | Validated |
|---|---|---|---|
| `chk_seasons_date_order` | Check | `CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)` | True |
| `seasons_league_id_fkey` | Foreign key | `FOREIGN KEY (league_id) REFERENCES leagues(id)` | True |
| `seasons_pkey` | Primary key | `PRIMARY KEY (id)` | True |

### Indexes

| Index | Definition | Valid / ready |
|---|---|---|
| `seasons_pkey` | `CREATE UNIQUE INDEX seasons_pkey ON public.seasons USING btree (id)` | True / True |

## `teams`

Teams associated directly with a sport, not directly with a league.

Origin: Sprint 1 SQL, commit `1202e94` (2026-09-15).

| Column | PostgreSQL type | Nullable | Default / identity | Keys |
|---|---|---|---|---|
| `id` | `BIGINT` | No | `nextval('"public".teams_id_seq'::regclass)` | PK |
| `sport_id` | `BIGINT` | Yes | `—` | FK → sports.id |
| `name` | `VARCHAR(140)` | No | `—` | — |
| `abbreviation` | `VARCHAR(20)` | Yes | `—` | — |
| `city` | `VARCHAR(100)` | Yes | `—` | — |
| `logo_url` | `TEXT` | Yes | `—` | — |
| `active` | `BOOLEAN` | Yes | `true` | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Yes | `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | Yes | `now()` | — |

### Constraints

| Name | Kind | Verified PostgreSQL definition | Validated |
|---|---|---|---|
| `teams_pkey` | Primary key | `PRIMARY KEY (id)` | True |
| `teams_sport_id_fkey` | Foreign key | `FOREIGN KEY (sport_id) REFERENCES sports(id)` | True |

### Indexes

| Index | Definition | Valid / ready |
|---|---|---|
| `teams_pkey` | `CREATE UNIQUE INDEX teams_pkey ON public.teams USING btree (id)` | True / True |

## `season_teams`

Many-to-many season/team membership, with conference/division context.

Origin: Sprint 1 SQL, commit `1202e94` (2026-09-15).

| Column | PostgreSQL type | Nullable | Default / identity | Keys |
|---|---|---|---|---|
| `season_id` | `BIGINT` | No | `—` | PK (composite); FK → seasons.id |
| `team_id` | `BIGINT` | No | `—` | PK (composite); FK → teams.id |
| `conference_name` | `VARCHAR(80)` | Yes | `—` | — |
| `division_name` | `VARCHAR(80)` | Yes | `—` | — |

### Constraints

| Name | Kind | Verified PostgreSQL definition | Validated |
|---|---|---|---|
| `season_teams_pkey` | Primary key | `PRIMARY KEY (season_id, team_id)` | True |
| `season_teams_season_id_fkey` | Foreign key | `FOREIGN KEY (season_id) REFERENCES seasons(id)` | True |
| `season_teams_team_id_fkey` | Foreign key | `FOREIGN KEY (team_id) REFERENCES teams(id)` | True |

### Indexes

| Index | Definition | Valid / ready |
|---|---|---|
| `season_teams_pkey` | `CREATE UNIQUE INDEX season_teams_pkey ON public.season_teams USING btree (season_id, team_id)` | True / True |

## `matches`

Scheduled/completed matchups, team references, times and scores.

Origin: Sprint 1 SQL, commit `1202e94` (2026-09-15).

| Column | PostgreSQL type | Nullable | Default / identity | Keys |
|---|---|---|---|---|
| `id` | `BIGINT` | No | `nextval('"public".matches_id_seq'::regclass)` | PK |
| `league_id` | `BIGINT` | Yes | `—` | FK → leagues.id |
| `season_id` | `BIGINT` | Yes | `—` | FK → seasons.id |
| `home_team_id` | `BIGINT` | Yes | `—` | FK → teams.id |
| `away_team_id` | `BIGINT` | Yes | `—` | FK → teams.id |
| `start_time` | `TIMESTAMP WITH TIME ZONE` | No | `—` | — |
| `status` | `VARCHAR(30)` | Yes | `—` | — |
| `home_score` | `INTEGER` | Yes | `—` | — |
| `away_score` | `INTEGER` | Yes | `—` | — |
| `neutral_site` | `BOOLEAN` | Yes | `false` | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Yes | `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | Yes | `now()` | — |

### Constraints

| Name | Kind | Verified PostgreSQL definition | Validated |
|---|---|---|---|
| `chk_matches_away_score_nonnegative` | Check | `CHECK (away_score IS NULL OR away_score >= 0)` | True |
| `chk_matches_different_teams` | Check | `CHECK (home_team_id IS NULL OR away_team_id IS NULL OR home_team_id <> away_team_id)` | True |
| `chk_matches_home_score_nonnegative` | Check | `CHECK (home_score IS NULL OR home_score >= 0)` | True |
| `chk_matches_status` | Check | `CHECK (status::text = ANY (ARRAY['scheduled'::character varying, 'in_progress'::character varying, 'final'::character varying, 'postponed'::character varying, 'cancelled'::character varying]::text[]))` | True |
| `matches_away_team_id_fkey` | Foreign key | `FOREIGN KEY (away_team_id) REFERENCES teams(id)` | True |
| `matches_home_team_id_fkey` | Foreign key | `FOREIGN KEY (home_team_id) REFERENCES teams(id)` | True |
| `matches_league_id_fkey` | Foreign key | `FOREIGN KEY (league_id) REFERENCES leagues(id)` | True |
| `matches_pkey` | Primary key | `PRIMARY KEY (id)` | True |
| `matches_season_id_fkey` | Foreign key | `FOREIGN KEY (season_id) REFERENCES seasons(id)` | True |

### Indexes

| Index | Definition | Valid / ready |
|---|---|---|
| `idx_matches_away_team_id` | `CREATE INDEX idx_matches_away_team_id ON public.matches USING btree (away_team_id)` | True / True |
| `idx_matches_home_team_id` | `CREATE INDEX idx_matches_home_team_id ON public.matches USING btree (home_team_id)` | True / True |
| `idx_matches_league_start_time` | `CREATE INDEX idx_matches_league_start_time ON public.matches USING btree (league_id, start_time)` | True / True |
| `idx_matches_start_time` | `CREATE INDEX idx_matches_start_time ON public.matches USING btree (start_time)` | True / True |
| `matches_pkey` | `CREATE UNIQUE INDEX matches_pkey ON public.matches USING btree (id)` | True / True |

## `match_predictions`

Stored model prediction schema; table existence does not prove current endpoints write predictions.

Origin: Sprint 1 SQL, commit `1202e94` (2026-09-15).

| Column | PostgreSQL type | Nullable | Default / identity | Keys |
|---|---|---|---|---|
| `id` | `BIGINT` | No | `nextval('"public".match_predictions_id_seq'::regclass)` | PK |
| `match_id` | `BIGINT` | Yes | `—` | FK → matches.id; composite UNIQUE (match_id, model_version_id) |
| `model_version_id` | `BIGINT` | Yes | `—` | FK → model_versions.id; composite UNIQUE (match_id, model_version_id) |
| `predicted_winner_id` | `BIGINT` | Yes | `—` | FK → teams.id |
| `home_win_probability` | `NUMERIC(5, 4)` | Yes | `—` | — |
| `away_win_probability` | `NUMERIC(5, 4)` | Yes | `—` | — |
| `confidence` | `NUMERIC(5, 4)` | Yes | `—` | — |
| `generated_at` | `TIMESTAMP WITH TIME ZONE` | Yes | `now()` | — |
| `explanation_json` | `JSONB` | Yes | `—` | — |

### Constraints

| Name | Kind | Verified PostgreSQL definition | Validated |
|---|---|---|---|
| `chk_match_predictions_away_probability` | Check | `CHECK (away_win_probability IS NULL OR away_win_probability >= 0::numeric AND away_win_probability <= 1::numeric)` | True |
| `chk_match_predictions_confidence` | Check | `CHECK (confidence IS NULL OR confidence >= 0::numeric AND confidence <= 1::numeric)` | True |
| `chk_match_predictions_home_probability` | Check | `CHECK (home_win_probability IS NULL OR home_win_probability >= 0::numeric AND home_win_probability <= 1::numeric)` | True |
| `match_predictions_match_id_fkey` | Foreign key | `FOREIGN KEY (match_id) REFERENCES matches(id)` | True |
| `match_predictions_model_version_id_fkey` | Foreign key | `FOREIGN KEY (model_version_id) REFERENCES model_versions(id)` | True |
| `match_predictions_pkey` | Primary key | `PRIMARY KEY (id)` | True |
| `match_predictions_predicted_winner_id_fkey` | Foreign key | `FOREIGN KEY (predicted_winner_id) REFERENCES teams(id)` | True |
| `uq_match_predictions_match_model` | Unique | `UNIQUE (match_id, model_version_id)` | True |

### Indexes

| Index | Definition | Valid / ready |
|---|---|---|
| `idx_match_predictions_match_id` | `CREATE INDEX idx_match_predictions_match_id ON public.match_predictions USING btree (match_id)` | True / True |
| `match_predictions_pkey` | `CREATE UNIQUE INDEX match_predictions_pkey ON public.match_predictions USING btree (id)` | True / True |
| `uq_match_predictions_match_model` | `CREATE UNIQUE INDEX uq_match_predictions_match_model ON public.match_predictions USING btree (match_id, model_version_id)` | True / True |

## `model_versions`

Prediction model metadata and metrics.

Origin: Sprint 1 SQL, commit `1202e94` (2026-09-15).

| Column | PostgreSQL type | Nullable | Default / identity | Keys |
|---|---|---|---|---|
| `id` | `BIGINT` | No | `nextval('"public".model_versions_id_seq'::regclass)` | PK |
| `name` | `VARCHAR(120)` | No | `—` | — |
| `version` | `VARCHAR(50)` | No | `—` | — |
| `algorithm` | `VARCHAR(120)` | Yes | `—` | — |
| `training_cutoff` | `TIMESTAMP WITH TIME ZONE` | Yes | `—` | — |
| `metrics_json` | `JSONB` | Yes | `—` | — |
| `active` | `BOOLEAN` | Yes | `true` | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Yes | `now()` | — |

### Constraints

| Name | Kind | Verified PostgreSQL definition | Validated |
|---|---|---|---|
| `model_versions_pkey` | Primary key | `PRIMARY KEY (id)` | True |

### Indexes

| Index | Definition | Valid / ready |
|---|---|---|
| `model_versions_pkey` | `CREATE UNIQUE INDEX model_versions_pkey ON public.model_versions USING btree (id)` | True / True |

## `user_predictions`

Per-user match picks; separate from virtual bets and model predictions.

Origin: Sprint 1 SQL, commit `1202e94` (2026-09-15).

| Column | PostgreSQL type | Nullable | Default / identity | Keys |
|---|---|---|---|---|
| `id` | `BIGINT` | No | `nextval('"public".user_predictions_id_seq'::regclass)` | PK |
| `user_id` | `BIGINT` | Yes | `—` | FK → users.id; composite UNIQUE (user_id, match_id) |
| `match_id` | `BIGINT` | Yes | `—` | FK → matches.id; composite UNIQUE (user_id, match_id) |
| `predicted_winner_id` | `BIGINT` | Yes | `—` | FK → teams.id |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Yes | `now()` | — |
| `is_correct` | `BOOLEAN` | Yes | `—` | — |

### Constraints

| Name | Kind | Verified PostgreSQL definition | Validated |
|---|---|---|---|
| `uq_user_predictions_user_match` | Unique | `UNIQUE (user_id, match_id)` | True |
| `user_predictions_match_id_fkey` | Foreign key | `FOREIGN KEY (match_id) REFERENCES matches(id)` | True |
| `user_predictions_pkey` | Primary key | `PRIMARY KEY (id)` | True |
| `user_predictions_predicted_winner_id_fkey` | Foreign key | `FOREIGN KEY (predicted_winner_id) REFERENCES teams(id)` | True |
| `user_predictions_user_id_fkey` | Foreign key | `FOREIGN KEY (user_id) REFERENCES users(id)` | True |

### Indexes

| Index | Definition | Valid / ready |
|---|---|---|
| `idx_user_predictions_match_id` | `CREATE INDEX idx_user_predictions_match_id ON public.user_predictions USING btree (match_id)` | True / True |
| `idx_user_predictions_user_id` | `CREATE INDEX idx_user_predictions_user_id ON public.user_predictions USING btree (user_id)` | True / True |
| `uq_user_predictions_user_match` | `CREATE UNIQUE INDEX uq_user_predictions_user_match ON public.user_predictions USING btree (user_id, match_id)` | True / True |
| `user_predictions_pkey` | `CREATE UNIQUE INDEX user_predictions_pkey ON public.user_predictions USING btree (id)` | True / True |

## `users`

Persistent accounts; password_hash stores bcrypt output, never plaintext passwords.

Origin: Sprint 1 SQL, commit `1202e94` (2026-09-15).

| Column | PostgreSQL type | Nullable | Default / identity | Keys |
|---|---|---|---|---|
| `id` | `BIGINT` | No | `nextval('"public".users_id_seq'::regclass)` | PK |
| `email` | `VARCHAR(254)` | No | `—` | UNIQUE |
| `username` | `VARCHAR(80)` | Yes | `—` | UNIQUE |
| `display_name` | `VARCHAR(120)` | Yes | `—` | — |
| `is_active` | `BOOLEAN` | Yes | `true` | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Yes | `now()` | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | Yes | `now()` | — |
| `password_hash` | `VARCHAR(255)` | No | `—` | — |

### Constraints

| Name | Kind | Verified PostgreSQL definition | Validated |
|---|---|---|---|
| `users_email_key` | Unique | `UNIQUE (email)` | True |
| `users_pkey` | Primary key | `PRIMARY KEY (id)` | True |
| `users_username_key` | Unique | `UNIQUE (username)` | True |

### Indexes

| Index | Definition | Valid / ready |
|---|---|---|
| `users_email_key` | `CREATE UNIQUE INDEX users_email_key ON public.users USING btree (email)` | True / True |
| `users_pkey` | `CREATE UNIQUE INDEX users_pkey ON public.users USING btree (id)` | True / True |
| `users_username_key` | `CREATE UNIQUE INDEX users_username_key ON public.users USING btree (username)` | True / True |

## `data_sources`

Source catalogue for ingestion.

Origin: Sprint 1 SQL, commit `1202e94` (2026-09-15).

| Column | PostgreSQL type | Nullable | Default / identity | Keys |
|---|---|---|---|---|
| `id` | `BIGINT` | No | `nextval('"public".data_sources_id_seq'::regclass)` | PK |
| `name` | `VARCHAR(100)` | No | `—` | UNIQUE |
| `base_url` | `TEXT` | Yes | `—` | — |
| `source_type` | `VARCHAR(30)` | Yes | `—` | — |
| `active` | `BOOLEAN` | Yes | `true` | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Yes | `now()` | — |

### Constraints

| Name | Kind | Verified PostgreSQL definition | Validated |
|---|---|---|---|
| `chk_data_sources_source_type` | Check | `CHECK (source_type::text = ANY (ARRAY['api'::character varying, 'manual'::character varying, 'file'::character varying]::text[]))` | True |
| `data_sources_name_key` | Unique | `UNIQUE (name)` | True |
| `data_sources_pkey` | Primary key | `PRIMARY KEY (id)` | True |

### Indexes

| Index | Definition | Valid / ready |
|---|---|---|
| `data_sources_name_key` | `CREATE UNIQUE INDEX data_sources_name_key ON public.data_sources USING btree (name)` | True / True |
| `data_sources_pkey` | `CREATE UNIQUE INDEX data_sources_pkey ON public.data_sources USING btree (id)` | True / True |

## `external_mappings`

Provider identifiers; entity_id is a polymorphic application reference, not a database FK.

Origin: Sprint 1 SQL, commit `1202e94` (2026-09-15).

| Column | PostgreSQL type | Nullable | Default / identity | Keys |
|---|---|---|---|---|
| `id` | `BIGINT` | No | `nextval('"public".external_mappings_id_seq'::regclass)` | PK |
| `data_source_id` | `BIGINT` | Yes | `—` | FK → data_sources.id; composite UNIQUE (data_source_id, entity_type, external_id) |
| `entity_type` | `VARCHAR(30)` | Yes | `—` | composite UNIQUE (data_source_id, entity_type, external_id) |
| `entity_id` | `BIGINT` | No | `—` | — |
| `external_id` | `VARCHAR(160)` | No | `—` | composite UNIQUE (data_source_id, entity_type, external_id) |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Yes | `now()` | — |

### Constraints

| Name | Kind | Verified PostgreSQL definition | Validated |
|---|---|---|---|
| `chk_external_mappings_entity_type` | Check | `CHECK (entity_type::text = ANY (ARRAY['league'::character varying, 'season'::character varying, 'team'::character varying, 'match'::character varying]::text[]))` | True |
| `external_mappings_data_source_id_fkey` | Foreign key | `FOREIGN KEY (data_source_id) REFERENCES data_sources(id)` | True |
| `external_mappings_pkey` | Primary key | `PRIMARY KEY (id)` | True |
| `uq_external_mappings_provider_entity` | Unique | `UNIQUE (data_source_id, entity_type, external_id)` | True |

### Indexes

| Index | Definition | Valid / ready |
|---|---|---|
| `external_mappings_pkey` | `CREATE UNIQUE INDEX external_mappings_pkey ON public.external_mappings USING btree (id)` | True / True |
| `uq_external_mappings_provider_entity` | `CREATE UNIQUE INDEX uq_external_mappings_provider_entity ON public.external_mappings USING btree (data_source_id, entity_type, external_id)` | True / True |

## `ingestion_runs`

Ingestion execution metadata.

Origin: Sprint 1 SQL, commit `1202e94` (2026-09-15).

| Column | PostgreSQL type | Nullable | Default / identity | Keys |
|---|---|---|---|---|
| `id` | `BIGINT` | No | `nextval('"public".ingestion_runs_id_seq'::regclass)` | PK |
| `data_source_id` | `BIGINT` | Yes | `—` | FK → data_sources.id |
| `started_at` | `TIMESTAMP WITH TIME ZONE` | Yes | `now()` | — |
| `completed_at` | `TIMESTAMP WITH TIME ZONE` | Yes | `—` | — |
| `status` | `VARCHAR(20)` | Yes | `—` | — |
| `records_read` | `INTEGER` | Yes | `0` | — |
| `records_written` | `INTEGER` | Yes | `0` | — |
| `error_message` | `TEXT` | Yes | `—` | — |

### Constraints

| Name | Kind | Verified PostgreSQL definition | Validated |
|---|---|---|---|
| `chk_ingestion_runs_status` | Check | `CHECK (status::text = ANY (ARRAY['running'::character varying, 'success'::character varying, 'failed'::character varying]::text[]))` | True |
| `ingestion_runs_data_source_id_fkey` | Foreign key | `FOREIGN KEY (data_source_id) REFERENCES data_sources(id)` | True |
| `ingestion_runs_pkey` | Primary key | `PRIMARY KEY (id)` | True |

### Indexes

| Index | Definition | Valid / ready |
|---|---|---|
| `idx_ingestion_runs_source_started_at` | `CREATE INDEX idx_ingestion_runs_source_started_at ON public.ingestion_runs USING btree (data_source_id, started_at DESC)` | True / True |
| `ingestion_runs_pkey` | `CREATE UNIQUE INDEX ingestion_runs_pkey ON public.ingestion_runs USING btree (id)` | True / True |

## `auth_sessions`

Persistent sessions keyed by digest; user FK and expiry enable lookup/revocation. No token values are included here.

Origin: Auth definitions introduced in Sprint 4, commit `2a4223e` (2026-11-05); created in this local DB during Sprint 5 setup.

| Column | PostgreSQL type | Nullable | Default / identity | Keys |
|---|---|---|---|---|
| `token_digest` | `VARCHAR(64)` | No | `—` | PK |
| `user_id` | `BIGINT` | No | `—` | FK → users.id |
| `csrf_token` | `VARCHAR(43)` | No | `—` | — |
| `expires_at` | `DOUBLE PRECISION` | No | `—` | — |

### Constraints

| Name | Kind | Verified PostgreSQL definition | Validated |
|---|---|---|---|
| `auth_sessions_pkey` | Primary key | `PRIMARY KEY (token_digest)` | True |
| `auth_sessions_user_id_fkey` | Foreign key | `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE` | True |

### Indexes

| Index | Definition | Valid / ready |
|---|---|---|
| `auth_sessions_pkey` | `CREATE UNIQUE INDEX auth_sessions_pkey ON public.auth_sessions USING btree (token_digest)` | True / True |
| `ix_auth_sessions_expires_at` | `CREATE INDEX ix_auth_sessions_expires_at ON public.auth_sessions USING btree (expires_at)` | True / True |

## `auth_csrf_challenges`

Pre-login challenge digests, CSRF material and expiration; no user FK by design.

Origin: Auth definitions introduced in Sprint 4, commit `2a4223e` (2026-11-05); created in this local DB during Sprint 5 setup.

| Column | PostgreSQL type | Nullable | Default / identity | Keys |
|---|---|---|---|---|
| `nonce_digest` | `VARCHAR(64)` | No | `—` | PK |
| `csrf_token` | `VARCHAR(43)` | No | `—` | — |
| `expires_at` | `DOUBLE PRECISION` | No | `—` | — |

### Constraints

| Name | Kind | Verified PostgreSQL definition | Validated |
|---|---|---|---|
| `auth_csrf_challenges_pkey` | Primary key | `PRIMARY KEY (nonce_digest)` | True |

### Indexes

| Index | Definition | Valid / ready |
|---|---|---|
| `auth_csrf_challenges_pkey` | `CREATE UNIQUE INDEX auth_csrf_challenges_pkey ON public.auth_csrf_challenges USING btree (nonce_digest)` | True / True |
| `ix_auth_csrf_challenges_expires_at` | `CREATE INDEX ix_auth_csrf_challenges_expires_at ON public.auth_csrf_challenges USING btree (expires_at)` | True / True |

## `auth_login_attempts`

Account-derived digest keys, failure history and temporary login blocking; no user FK so nonexistent accounts can be throttled.

Origin: Auth definitions introduced in Sprint 4, commit `2a4223e` (2026-11-05); created in this local DB during Sprint 5 setup.

| Column | PostgreSQL type | Nullable | Default / identity | Keys |
|---|---|---|---|---|
| `key_digest` | `VARCHAR(64)` | No | `—` | PK |
| `window_start` | `DOUBLE PRECISION` | No | `—` | — |
| `failure_count` | `INTEGER` | No | `—` | — |
| `blocked_until` | `DOUBLE PRECISION` | No | `—` | — |
| `failure_times` | `JSON` | No | `'[]'::json` | — |

### Constraints

| Name | Kind | Verified PostgreSQL definition | Validated |
|---|---|---|---|
| `auth_login_attempts_pkey` | Primary key | `PRIMARY KEY (key_digest)` | True |

### Indexes

| Index | Definition | Valid / ready |
|---|---|---|
| `auth_login_attempts_pkey` | `CREATE UNIQUE INDEX auth_login_attempts_pkey ON public.auth_login_attempts USING btree (key_digest)` | True / True |

## `auth_assessment_records`

Synthetic Sprint 4 ownership-assessment records; not bet history or an operational wallet table.

Origin: Auth definitions introduced in Sprint 4, commit `2a4223e` (2026-11-05); created in this local DB during Sprint 5 setup.

| Column | PostgreSQL type | Nullable | Default / identity | Keys |
|---|---|---|---|---|
| `id` | `BIGINT` | No | `nextval('"public".auth_assessment_records_id_seq'::regclass)` | PK |
| `owner_id` | `BIGINT` | No | `—` | FK → users.id |
| `note` | `TEXT` | No | `—` | — |

### Constraints

| Name | Kind | Verified PostgreSQL definition | Validated |
|---|---|---|---|
| `auth_assessment_records_owner_id_fkey` | Foreign key | `FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE` | True |
| `auth_assessment_records_pkey` | Primary key | `PRIMARY KEY (id)` | True |

### Indexes

| Index | Definition | Valid / ready |
|---|---|---|
| `auth_assessment_records_pkey` | `CREATE UNIQUE INDEX auth_assessment_records_pkey ON public.auth_assessment_records USING btree (id)` | True / True |

## `virtual_wallets`

One virtual-points balance per user; initial 1,000-point credit is application logic, not a SQL default.

Origin: Sprint 5 virtual-betting implementation; Sprint 5 feature-branch files.

| Column | PostgreSQL type | Nullable | Default / identity | Keys |
|---|---|---|---|---|
| `user_id` | `BIGINT` | No | `—` | PK; FK → users.id |
| `balance` | `INTEGER` | No | `—` | — |

### Constraints

| Name | Kind | Verified PostgreSQL definition | Validated |
|---|---|---|---|
| `virtual_wallets_balance_check` | Check | `CHECK (balance >= 0)` | True |
| `virtual_wallets_pkey` | Primary key | `PRIMARY KEY (user_id)` | True |
| `virtual_wallets_user_id_fkey` | Foreign key | `FOREIGN KEY (user_id) REFERENCES users(id)` | True |

### Indexes

| Index | Definition | Valid / ready |
|---|---|---|
| `virtual_wallets_pkey` | `CREATE UNIQUE INDEX virtual_wallets_pkey ON public.virtual_wallets USING btree (user_id)` | True / True |

## `demo_markets`

At most one single-match winner market per match.

Origin: Sprint 5 virtual-betting implementation; Sprint 5 feature-branch files.

| Column | PostgreSQL type | Nullable | Default / identity | Keys |
|---|---|---|---|---|
| `id` | `BIGINT` | No | `nextval('"public".demo_markets_id_seq'::regclass)` | PK |
| `match_id` | `BIGINT` | No | `—` | FK → matches.id; UNIQUE |
| `is_open` | `BOOLEAN` | No | `true` | — |

### Constraints

| Name | Kind | Verified PostgreSQL definition | Validated |
|---|---|---|---|
| `demo_markets_match_id_fkey` | Foreign key | `FOREIGN KEY (match_id) REFERENCES matches(id)` | True |
| `demo_markets_match_id_key` | Unique | `UNIQUE (match_id)` | True |
| `demo_markets_pkey` | Primary key | `PRIMARY KEY (id)` | True |

### Indexes

| Index | Definition | Valid / ready |
|---|---|---|
| `demo_markets_match_id_key` | `CREATE UNIQUE INDEX demo_markets_match_id_key ON public.demo_markets USING btree (match_id)` | True / True |
| `demo_markets_pkey` | `CREATE UNIQUE INDEX demo_markets_pkey ON public.demo_markets USING btree (id)` | True / True |

## `virtual_wallet_transactions`

Signed integer ledger amounts; application reference strings support retry protection. No real currency.

Origin: Sprint 5 virtual-betting implementation; Sprint 5 feature-branch files.

| Column | PostgreSQL type | Nullable | Default / identity | Keys |
|---|---|---|---|---|
| `id` | `BIGINT` | No | `nextval('"public".virtual_wallet_transactions_id_seq'::regclass)` | PK |
| `user_id` | `BIGINT` | No | `—` | FK → users.id; composite UNIQUE (user_id, reference) |
| `amount` | `INTEGER` | No | `—` | — |
| `kind` | `VARCHAR(20)` | No | `—` | — |
| `reference` | `VARCHAR(120)` | No | `—` | composite UNIQUE (user_id, reference) |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Yes | `CURRENT_TIMESTAMP` | — |

### Constraints

| Name | Kind | Verified PostgreSQL definition | Validated |
|---|---|---|---|
| `virtual_wallet_transactions_pkey` | Primary key | `PRIMARY KEY (id)` | True |
| `virtual_wallet_transactions_user_id_fkey` | Foreign key | `FOREIGN KEY (user_id) REFERENCES users(id)` | True |
| `virtual_wallet_transactions_user_id_reference_key` | Unique | `UNIQUE (user_id, reference)` | True |

### Indexes

| Index | Definition | Valid / ready |
|---|---|---|
| `virtual_wallet_transactions_pkey` | `CREATE UNIQUE INDEX virtual_wallet_transactions_pkey ON public.virtual_wallet_transactions USING btree (id)` | True / True |
| `virtual_wallet_transactions_user_id_reference_key` | `CREATE UNIQUE INDEX virtual_wallet_transactions_user_id_reference_key ON public.virtual_wallet_transactions USING btree (user_id, reference)` | True / True |

## `demo_outcomes`

Stored synthetic decimal odds for home/away and EPL draw selections.

Origin: Sprint 5 virtual-betting implementation; Sprint 5 feature-branch files.

| Column | PostgreSQL type | Nullable | Default / identity | Keys |
|---|---|---|---|---|
| `id` | `BIGINT` | No | `nextval('"public".demo_outcomes_id_seq'::regclass)` | PK |
| `market_id` | `BIGINT` | No | `—` | FK → demo_markets.id; composite UNIQUE (market_id, selection) |
| `selection` | `VARCHAR(10)` | No | `—` | composite UNIQUE (market_id, selection) |
| `decimal_odds` | `NUMERIC(9, 4)` | No | `—` | — |

### Constraints

| Name | Kind | Verified PostgreSQL definition | Validated |
|---|---|---|---|
| `demo_outcomes_decimal_odds_check` | Check | `CHECK (decimal_odds > 1::numeric AND decimal_odds <= 1000::numeric)` | True |
| `demo_outcomes_market_id_fkey` | Foreign key | `FOREIGN KEY (market_id) REFERENCES demo_markets(id)` | True |
| `demo_outcomes_market_id_selection_key` | Unique | `UNIQUE (market_id, selection)` | True |
| `demo_outcomes_pkey` | Primary key | `PRIMARY KEY (id)` | True |
| `demo_outcomes_selection_check` | Check | `CHECK (selection::text = ANY (ARRAY['home'::character varying, 'draw'::character varying, 'away'::character varying]::text[]))` | True |

### Indexes

| Index | Definition | Valid / ready |
|---|---|---|
| `demo_outcomes_market_id_selection_key` | `CREATE UNIQUE INDEX demo_outcomes_market_id_selection_key ON public.demo_outcomes USING btree (market_id, selection)` | True / True |
| `demo_outcomes_pkey` | `CREATE UNIQUE INDEX demo_outcomes_pkey ON public.demo_outcomes USING btree (id)` | True / True |

## `virtual_bets`

User-owned stake, accepted odds snapshot, potential payout, result status and idempotency key.

Origin: Sprint 5 virtual-betting implementation; Sprint 5 feature-branch files.

| Column | PostgreSQL type | Nullable | Default / identity | Keys |
|---|---|---|---|---|
| `id` | `BIGINT` | No | `nextval('"public".virtual_bets_id_seq'::regclass)` | PK |
| `user_id` | `BIGINT` | No | `—` | FK → users.id; composite UNIQUE (user_id, request_key) |
| `match_id` | `BIGINT` | No | `—` | FK → matches.id |
| `outcome_id` | `BIGINT` | No | `—` | FK → demo_outcomes.id |
| `selection` | `VARCHAR(10)` | No | `—` | — |
| `stake` | `INTEGER` | No | `—` | — |
| `accepted_odds` | `NUMERIC(9, 4)` | No | `—` | — |
| `potential_payout` | `INTEGER` | No | `—` | — |
| `status` | `VARCHAR(10)` | No | `'PENDING'::character varying` | — |
| `request_key` | `VARCHAR(100)` | No | `—` | composite UNIQUE (user_id, request_key) |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Yes | `CURRENT_TIMESTAMP` | — |

### Constraints

| Name | Kind | Verified PostgreSQL definition | Validated |
|---|---|---|---|
| `virtual_bets_check` | Check | `CHECK (potential_payout >= stake)` | True |
| `virtual_bets_match_id_fkey` | Foreign key | `FOREIGN KEY (match_id) REFERENCES matches(id)` | True |
| `virtual_bets_outcome_id_fkey` | Foreign key | `FOREIGN KEY (outcome_id) REFERENCES demo_outcomes(id)` | True |
| `virtual_bets_pkey` | Primary key | `PRIMARY KEY (id)` | True |
| `virtual_bets_stake_check` | Check | `CHECK (stake > 0)` | True |
| `virtual_bets_status_check` | Check | `CHECK (status::text = ANY (ARRAY['PENDING'::character varying, 'WON'::character varying, 'LOST'::character varying, 'VOID'::character varying]::text[]))` | True |
| `virtual_bets_user_id_fkey` | Foreign key | `FOREIGN KEY (user_id) REFERENCES users(id)` | True |
| `virtual_bets_user_id_request_key_key` | Unique | `UNIQUE (user_id, request_key)` | True |

### Indexes

| Index | Definition | Valid / ready |
|---|---|---|
| `virtual_bets_pkey` | `CREATE UNIQUE INDEX virtual_bets_pkey ON public.virtual_bets USING btree (id)` | True / True |
| `virtual_bets_user_id_request_key_key` | `CREATE UNIQUE INDEX virtual_bets_user_id_request_key_key ON public.virtual_bets USING btree (user_id, request_key)` | True / True |

## Sequences and identities

All 17 are BIGSERIAL-backed sequences owned by their indicated columns. No identity columns were found. Sequence definitions below deliberately omit live sequence counters (data state).

| Sequence | Owned column | Type | Start / increment | Min / max | Cache / cycle |
|---|---|---|---|---|---|
| `auth_assessment_records_id_seq` | `auth_assessment_records.id` | `bigint` | 1 / 1 | 1 / 9223372036854775807 | 1 / False |
| `data_sources_id_seq` | `data_sources.id` | `bigint` | 1 / 1 | 1 / 9223372036854775807 | 1 / False |
| `demo_markets_id_seq` | `demo_markets.id` | `bigint` | 1 / 1 | 1 / 9223372036854775807 | 1 / False |
| `demo_outcomes_id_seq` | `demo_outcomes.id` | `bigint` | 1 / 1 | 1 / 9223372036854775807 | 1 / False |
| `external_mappings_id_seq` | `external_mappings.id` | `bigint` | 1 / 1 | 1 / 9223372036854775807 | 1 / False |
| `ingestion_runs_id_seq` | `ingestion_runs.id` | `bigint` | 1 / 1 | 1 / 9223372036854775807 | 1 / False |
| `leagues_id_seq` | `leagues.id` | `bigint` | 1 / 1 | 1 / 9223372036854775807 | 1 / False |
| `match_predictions_id_seq` | `match_predictions.id` | `bigint` | 1 / 1 | 1 / 9223372036854775807 | 1 / False |
| `matches_id_seq` | `matches.id` | `bigint` | 1 / 1 | 1 / 9223372036854775807 | 1 / False |
| `model_versions_id_seq` | `model_versions.id` | `bigint` | 1 / 1 | 1 / 9223372036854775807 | 1 / False |
| `seasons_id_seq` | `seasons.id` | `bigint` | 1 / 1 | 1 / 9223372036854775807 | 1 / False |
| `sports_id_seq` | `sports.id` | `bigint` | 1 / 1 | 1 / 9223372036854775807 | 1 / False |
| `teams_id_seq` | `teams.id` | `bigint` | 1 / 1 | 1 / 9223372036854775807 | 1 / False |
| `user_predictions_id_seq` | `user_predictions.id` | `bigint` | 1 / 1 | 1 / 9223372036854775807 | 1 / False |
| `users_id_seq` | `users.id` | `bigint` | 1 / 1 | 1 / 9223372036854775807 | 1 / False |
| `virtual_bets_id_seq` | `virtual_bets.id` | `bigint` | 1 / 1 | 1 / 9223372036854775807 | 1 / False |
| `virtual_wallet_transactions_id_seq` | `virtual_wallet_transactions.id` | `bigint` | 1 / 1 | 1 / 9223372036854775807 | 1 / False |

## Relationships and enforcement boundaries

- Sports → leagues, sports → teams, leagues → seasons, and leagues/seasons → matches preserve the Sprint 1 structure. `season_teams` is the explicit season/team bridge. Home and away team FKs are separate edges.
- Users → sessions and assessment records; users → at most one wallet; matches → at most one demo market; markets → outcomes; users/matches/outcomes → bets; users → wallet ledger.
- Nullable historical FKs permit missing parents. All new user/market/bet FKs are NOT NULL. Only auth session/assessment user FKs specify ON DELETE CASCADE; other FKs use PostgreSQL default NO ACTION. Exact clauses appear above.
- `external_mappings.entity_id` is not a concrete FK. Ledger `reference` is not a bet FK; relationships through its string format are application conventions.
- Database CHECKs constrain wallet nonnegativity, outcome selection/odds, positive bet stake, payout at least stake and permitted bet status. No cross-table CHECK enforces that a bet outcome belongs to its stored match, that draw is EPL-only, or that team/season/league sport memberships agree. Placement validates its supported market rules in application code.
- `virtual_bets.accepted_odds` has no independent odds-range CHECK; the service verifies and snapshots an outcome with valid stored odds. Transaction `kind`, session expiry semantics, integer starting credits, ledger/balance reconciliation, payout rounding, schedule cutoff, duplicate-payload equality and settlement transitions are application responsibilities.
- No timestamp update trigger exists: `updated_at DEFAULT now()` sets an insertion default and does not automatically refresh on UPDATE.

## Other schema objects

User-schema views: 0; materialized views: 0; user-schema functions/procedures: 0; application triggers: 0. PostgreSQL system objects and the standard PL/pgSQL extension are not application-defined functions.
