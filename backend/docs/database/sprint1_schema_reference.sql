-- sports_prediction_schema.sql
-- CPSC 491-05 - Sprint 1
-- Sports Match-Prediction Application
-- PostgreSQL DDL based directly on Complete_Database_Schema_Sprint1.pdf
--
-- Proposed stack: FastAPI + PostgreSQL + SQLAlchemy + Alembic
-- Status: Team-review schema draft
--
-- Run this file while connected to the target PostgreSQL database.
-- This script creates the schema objects only; it does not create the database
-- and does not insert seed data.

BEGIN;

-- ============================================================
-- 4.1 sports
-- ============================================================
CREATE TABLE sports (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(80) NOT NULL UNIQUE,
    slug VARCHAR(80) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 4.2 leagues
-- ============================================================
CREATE TABLE leagues (
    id BIGSERIAL PRIMARY KEY,
    sport_id BIGINT REFERENCES sports(id),
    name VARCHAR(120) NOT NULL,
    abbreviation VARCHAR(30),
    country VARCHAR(80),
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 4.3 seasons
-- ============================================================
CREATE TABLE seasons (
    id BIGSERIAL PRIMARY KEY,
    league_id BIGINT REFERENCES leagues(id),
    name VARCHAR(60) NOT NULL,
    start_date DATE,
    end_date DATE,
    is_current BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT chk_seasons_date_order
        CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);

-- ============================================================
-- 4.4 teams
-- ============================================================
CREATE TABLE teams (
    id BIGSERIAL PRIMARY KEY,
    sport_id BIGINT REFERENCES sports(id),
    name VARCHAR(140) NOT NULL,
    abbreviation VARCHAR(20),
    city VARCHAR(100),
    logo_url TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 4.5 season_teams
-- ============================================================
CREATE TABLE season_teams (
    season_id BIGINT REFERENCES seasons(id),
    team_id BIGINT REFERENCES teams(id),
    conference_name VARCHAR(80),
    division_name VARCHAR(80),

    PRIMARY KEY (season_id, team_id)
);

-- ============================================================
-- 4.6 matches
-- ============================================================
CREATE TABLE matches (
    id BIGSERIAL PRIMARY KEY,
    league_id BIGINT REFERENCES leagues(id),
    season_id BIGINT REFERENCES seasons(id),
    home_team_id BIGINT REFERENCES teams(id),
    away_team_id BIGINT REFERENCES teams(id),
    start_time TIMESTAMPTZ NOT NULL,
    status VARCHAR(30),
    home_score INTEGER,
    away_score INTEGER,
    neutral_site BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT chk_matches_status
        CHECK (status IN (
            'scheduled',
            'in_progress',
            'final',
            'postponed',
            'cancelled'
        )),

    CONSTRAINT chk_matches_different_teams
        CHECK (home_team_id IS NULL OR away_team_id IS NULL OR home_team_id <> away_team_id),

    CONSTRAINT chk_matches_home_score_nonnegative
        CHECK (home_score IS NULL OR home_score >= 0),

    CONSTRAINT chk_matches_away_score_nonnegative
        CHECK (away_score IS NULL OR away_score >= 0)
);

-- ============================================================
-- 4.7 model_versions
-- ============================================================
CREATE TABLE model_versions (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    version VARCHAR(50) NOT NULL,
    algorithm VARCHAR(120),
    training_cutoff TIMESTAMPTZ,
    metrics_json JSONB,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 4.8 match_predictions
-- ============================================================
CREATE TABLE match_predictions (
    id BIGSERIAL PRIMARY KEY,
    match_id BIGINT REFERENCES matches(id),
    model_version_id BIGINT REFERENCES model_versions(id),
    predicted_winner_id BIGINT REFERENCES teams(id),
    home_win_probability NUMERIC(5,4),
    away_win_probability NUMERIC(5,4),
    confidence NUMERIC(5,4),
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    explanation_json JSONB,

    CONSTRAINT chk_match_predictions_home_probability
        CHECK (
            home_win_probability IS NULL
            OR home_win_probability BETWEEN 0 AND 1
        ),

    CONSTRAINT chk_match_predictions_away_probability
        CHECK (
            away_win_probability IS NULL
            OR away_win_probability BETWEEN 0 AND 1
        ),

    CONSTRAINT chk_match_predictions_confidence
        CHECK (
            confidence IS NULL
            OR confidence BETWEEN 0 AND 1
        ),

    CONSTRAINT uq_match_predictions_match_model
        UNIQUE (match_id, model_version_id)
);

-- ============================================================
-- 4.9 users
-- ============================================================
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(254) NOT NULL UNIQUE,
    username VARCHAR(80) UNIQUE,
    display_name VARCHAR(120),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 4.10 user_predictions
-- ============================================================
CREATE TABLE user_predictions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    match_id BIGINT REFERENCES matches(id),
    predicted_winner_id BIGINT REFERENCES teams(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_correct BOOLEAN,

    CONSTRAINT uq_user_predictions_user_match
        UNIQUE (user_id, match_id)
);

-- ============================================================
-- 4.11 data_sources
-- ============================================================
CREATE TABLE data_sources (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    base_url TEXT,
    source_type VARCHAR(30),
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT chk_data_sources_source_type
        CHECK (source_type IN ('api', 'manual', 'file'))
);

-- ============================================================
-- 4.12 external_mappings
-- ============================================================
CREATE TABLE external_mappings (
    id BIGSERIAL PRIMARY KEY,
    data_source_id BIGINT REFERENCES data_sources(id),
    entity_type VARCHAR(30),
    entity_id BIGINT NOT NULL,
    external_id VARCHAR(160) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT chk_external_mappings_entity_type
        CHECK (entity_type IN ('league', 'season', 'team', 'match')),

    CONSTRAINT uq_external_mappings_provider_entity
        UNIQUE (data_source_id, entity_type, external_id)
);

-- ============================================================
-- 4.13 ingestion_runs
-- ============================================================
CREATE TABLE ingestion_runs (
    id BIGSERIAL PRIMARY KEY,
    data_source_id BIGINT REFERENCES data_sources(id),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status VARCHAR(20),
    records_read INTEGER DEFAULT 0,
    records_written INTEGER DEFAULT 0,
    error_message TEXT,

    CONSTRAINT chk_ingestion_runs_status
        CHECK (status IN ('running', 'success', 'failed'))
);

-- ============================================================
-- 7. Recommended indexes
-- ============================================================
CREATE INDEX idx_matches_start_time
    ON matches(start_time);

CREATE INDEX idx_matches_league_start_time
    ON matches(league_id, start_time);

CREATE INDEX idx_matches_home_team_id
    ON matches(home_team_id);

CREATE INDEX idx_matches_away_team_id
    ON matches(away_team_id);

CREATE INDEX idx_match_predictions_match_id
    ON match_predictions(match_id);

CREATE INDEX idx_user_predictions_user_id
    ON user_predictions(user_id);

CREATE INDEX idx_user_predictions_match_id
    ON user_predictions(match_id);

CREATE INDEX idx_ingestion_runs_source_started_at
    ON ingestion_runs(data_source_id, started_at DESC);

COMMIT;
