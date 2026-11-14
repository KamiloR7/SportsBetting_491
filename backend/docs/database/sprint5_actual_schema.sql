--
-- PostgreSQL database dump
--


-- Dumped from database version 17.11 (Homebrew)
-- Dumped by pg_dump version 17.11 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: auth_assessment_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_assessment_records (
    id bigint NOT NULL,
    owner_id bigint NOT NULL,
    note text NOT NULL
);


--
-- Name: auth_assessment_records_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.auth_assessment_records_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: auth_assessment_records_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.auth_assessment_records_id_seq OWNED BY public.auth_assessment_records.id;


--
-- Name: auth_csrf_challenges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_csrf_challenges (
    nonce_digest character varying(64) NOT NULL,
    csrf_token character varying(43) NOT NULL,
    expires_at double precision NOT NULL
);


--
-- Name: auth_login_attempts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_login_attempts (
    key_digest character varying(64) NOT NULL,
    window_start double precision NOT NULL,
    failure_count integer NOT NULL,
    blocked_until double precision NOT NULL,
    failure_times json DEFAULT '[]'::json NOT NULL
);


--
-- Name: auth_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_sessions (
    token_digest character varying(64) NOT NULL,
    user_id bigint NOT NULL,
    csrf_token character varying(43) NOT NULL,
    expires_at double precision NOT NULL
);


--
-- Name: data_sources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.data_sources (
    id bigint NOT NULL,
    name character varying(100) NOT NULL,
    base_url text,
    source_type character varying(30),
    active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT chk_data_sources_source_type CHECK (((source_type)::text = ANY ((ARRAY['api'::character varying, 'manual'::character varying, 'file'::character varying])::text[])))
);


--
-- Name: data_sources_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.data_sources_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: data_sources_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.data_sources_id_seq OWNED BY public.data_sources.id;


--
-- Name: demo_markets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.demo_markets (
    id bigint NOT NULL,
    match_id bigint NOT NULL,
    is_open boolean DEFAULT true NOT NULL
);


--
-- Name: demo_markets_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.demo_markets_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: demo_markets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.demo_markets_id_seq OWNED BY public.demo_markets.id;


--
-- Name: demo_outcomes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.demo_outcomes (
    id bigint NOT NULL,
    market_id bigint NOT NULL,
    selection character varying(10) NOT NULL,
    decimal_odds numeric(9,4) NOT NULL,
    CONSTRAINT demo_outcomes_decimal_odds_check CHECK (((decimal_odds > (1)::numeric) AND (decimal_odds <= (1000)::numeric))),
    CONSTRAINT demo_outcomes_selection_check CHECK (((selection)::text = ANY ((ARRAY['home'::character varying, 'draw'::character varying, 'away'::character varying])::text[])))
);


--
-- Name: demo_outcomes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.demo_outcomes_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: demo_outcomes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.demo_outcomes_id_seq OWNED BY public.demo_outcomes.id;


--
-- Name: external_mappings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.external_mappings (
    id bigint NOT NULL,
    data_source_id bigint,
    entity_type character varying(30),
    entity_id bigint NOT NULL,
    external_id character varying(160) NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT chk_external_mappings_entity_type CHECK (((entity_type)::text = ANY ((ARRAY['league'::character varying, 'season'::character varying, 'team'::character varying, 'match'::character varying])::text[])))
);


--
-- Name: external_mappings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.external_mappings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: external_mappings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.external_mappings_id_seq OWNED BY public.external_mappings.id;


--
-- Name: ingestion_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ingestion_runs (
    id bigint NOT NULL,
    data_source_id bigint,
    started_at timestamp with time zone DEFAULT now(),
    completed_at timestamp with time zone,
    status character varying(20),
    records_read integer DEFAULT 0,
    records_written integer DEFAULT 0,
    error_message text,
    CONSTRAINT chk_ingestion_runs_status CHECK (((status)::text = ANY ((ARRAY['running'::character varying, 'success'::character varying, 'failed'::character varying])::text[])))
);


--
-- Name: ingestion_runs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ingestion_runs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ingestion_runs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ingestion_runs_id_seq OWNED BY public.ingestion_runs.id;


--
-- Name: leagues; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.leagues (
    id bigint NOT NULL,
    sport_id bigint,
    name character varying(120) NOT NULL,
    abbreviation character varying(30),
    country character varying(80),
    active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: leagues_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.leagues_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: leagues_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.leagues_id_seq OWNED BY public.leagues.id;


--
-- Name: match_predictions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.match_predictions (
    id bigint NOT NULL,
    match_id bigint,
    model_version_id bigint,
    predicted_winner_id bigint,
    home_win_probability numeric(5,4),
    away_win_probability numeric(5,4),
    confidence numeric(5,4),
    generated_at timestamp with time zone DEFAULT now(),
    explanation_json jsonb,
    CONSTRAINT chk_match_predictions_away_probability CHECK (((away_win_probability IS NULL) OR ((away_win_probability >= (0)::numeric) AND (away_win_probability <= (1)::numeric)))),
    CONSTRAINT chk_match_predictions_confidence CHECK (((confidence IS NULL) OR ((confidence >= (0)::numeric) AND (confidence <= (1)::numeric)))),
    CONSTRAINT chk_match_predictions_home_probability CHECK (((home_win_probability IS NULL) OR ((home_win_probability >= (0)::numeric) AND (home_win_probability <= (1)::numeric))))
);


--
-- Name: match_predictions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.match_predictions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: match_predictions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.match_predictions_id_seq OWNED BY public.match_predictions.id;


--
-- Name: matches; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.matches (
    id bigint NOT NULL,
    league_id bigint,
    season_id bigint,
    home_team_id bigint,
    away_team_id bigint,
    start_time timestamp with time zone NOT NULL,
    status character varying(30),
    home_score integer,
    away_score integer,
    neutral_site boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT chk_matches_away_score_nonnegative CHECK (((away_score IS NULL) OR (away_score >= 0))),
    CONSTRAINT chk_matches_different_teams CHECK (((home_team_id IS NULL) OR (away_team_id IS NULL) OR (home_team_id <> away_team_id))),
    CONSTRAINT chk_matches_home_score_nonnegative CHECK (((home_score IS NULL) OR (home_score >= 0))),
    CONSTRAINT chk_matches_status CHECK (((status)::text = ANY ((ARRAY['scheduled'::character varying, 'in_progress'::character varying, 'final'::character varying, 'postponed'::character varying, 'cancelled'::character varying])::text[])))
);


--
-- Name: matches_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.matches_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: matches_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.matches_id_seq OWNED BY public.matches.id;


--
-- Name: model_versions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.model_versions (
    id bigint NOT NULL,
    name character varying(120) NOT NULL,
    version character varying(50) NOT NULL,
    algorithm character varying(120),
    training_cutoff timestamp with time zone,
    metrics_json jsonb,
    active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: model_versions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.model_versions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: model_versions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.model_versions_id_seq OWNED BY public.model_versions.id;


--
-- Name: season_teams; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.season_teams (
    season_id bigint NOT NULL,
    team_id bigint NOT NULL,
    conference_name character varying(80),
    division_name character varying(80)
);


--
-- Name: seasons; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.seasons (
    id bigint NOT NULL,
    league_id bigint,
    name character varying(60) NOT NULL,
    start_date date,
    end_date date,
    is_current boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT chk_seasons_date_order CHECK (((end_date IS NULL) OR (start_date IS NULL) OR (end_date >= start_date)))
);


--
-- Name: seasons_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.seasons_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: seasons_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.seasons_id_seq OWNED BY public.seasons.id;


--
-- Name: sports; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sports (
    id bigint NOT NULL,
    name character varying(80) NOT NULL,
    slug character varying(80) NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: sports_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sports_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sports_id_seq OWNED BY public.sports.id;


--
-- Name: teams; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.teams (
    id bigint NOT NULL,
    sport_id bigint,
    name character varying(140) NOT NULL,
    abbreviation character varying(20),
    city character varying(100),
    logo_url text,
    active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: teams_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.teams_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: teams_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.teams_id_seq OWNED BY public.teams.id;


--
-- Name: user_predictions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_predictions (
    id bigint NOT NULL,
    user_id bigint,
    match_id bigint,
    predicted_winner_id bigint,
    created_at timestamp with time zone DEFAULT now(),
    is_correct boolean
);


--
-- Name: user_predictions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.user_predictions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_predictions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.user_predictions_id_seq OWNED BY public.user_predictions.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id bigint NOT NULL,
    email character varying(254) NOT NULL,
    username character varying(80),
    display_name character varying(120),
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    password_hash character varying(255) NOT NULL
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: virtual_bets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.virtual_bets (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    match_id bigint NOT NULL,
    outcome_id bigint NOT NULL,
    selection character varying(10) NOT NULL,
    stake integer NOT NULL,
    accepted_odds numeric(9,4) NOT NULL,
    potential_payout integer NOT NULL,
    status character varying(10) DEFAULT 'PENDING'::character varying NOT NULL,
    request_key character varying(100) NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT virtual_bets_check CHECK ((potential_payout >= stake)),
    CONSTRAINT virtual_bets_stake_check CHECK ((stake > 0)),
    CONSTRAINT virtual_bets_status_check CHECK (((status)::text = ANY ((ARRAY['PENDING'::character varying, 'WON'::character varying, 'LOST'::character varying, 'VOID'::character varying])::text[])))
);


--
-- Name: virtual_bets_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.virtual_bets_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: virtual_bets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.virtual_bets_id_seq OWNED BY public.virtual_bets.id;


--
-- Name: virtual_wallet_transactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.virtual_wallet_transactions (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    amount integer NOT NULL,
    kind character varying(20) NOT NULL,
    reference character varying(120) NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: virtual_wallet_transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.virtual_wallet_transactions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: virtual_wallet_transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.virtual_wallet_transactions_id_seq OWNED BY public.virtual_wallet_transactions.id;


--
-- Name: virtual_wallets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.virtual_wallets (
    user_id bigint NOT NULL,
    balance integer NOT NULL,
    CONSTRAINT virtual_wallets_balance_check CHECK ((balance >= 0))
);


--
-- Name: auth_assessment_records id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_assessment_records ALTER COLUMN id SET DEFAULT nextval('public.auth_assessment_records_id_seq'::regclass);


--
-- Name: data_sources id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_sources ALTER COLUMN id SET DEFAULT nextval('public.data_sources_id_seq'::regclass);


--
-- Name: demo_markets id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.demo_markets ALTER COLUMN id SET DEFAULT nextval('public.demo_markets_id_seq'::regclass);


--
-- Name: demo_outcomes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.demo_outcomes ALTER COLUMN id SET DEFAULT nextval('public.demo_outcomes_id_seq'::regclass);


--
-- Name: external_mappings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.external_mappings ALTER COLUMN id SET DEFAULT nextval('public.external_mappings_id_seq'::regclass);


--
-- Name: ingestion_runs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ingestion_runs ALTER COLUMN id SET DEFAULT nextval('public.ingestion_runs_id_seq'::regclass);


--
-- Name: leagues id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leagues ALTER COLUMN id SET DEFAULT nextval('public.leagues_id_seq'::regclass);


--
-- Name: match_predictions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_predictions ALTER COLUMN id SET DEFAULT nextval('public.match_predictions_id_seq'::regclass);


--
-- Name: matches id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.matches ALTER COLUMN id SET DEFAULT nextval('public.matches_id_seq'::regclass);


--
-- Name: model_versions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_versions ALTER COLUMN id SET DEFAULT nextval('public.model_versions_id_seq'::regclass);


--
-- Name: seasons id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seasons ALTER COLUMN id SET DEFAULT nextval('public.seasons_id_seq'::regclass);


--
-- Name: sports id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sports ALTER COLUMN id SET DEFAULT nextval('public.sports_id_seq'::regclass);


--
-- Name: teams id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams ALTER COLUMN id SET DEFAULT nextval('public.teams_id_seq'::regclass);


--
-- Name: user_predictions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_predictions ALTER COLUMN id SET DEFAULT nextval('public.user_predictions_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: virtual_bets id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.virtual_bets ALTER COLUMN id SET DEFAULT nextval('public.virtual_bets_id_seq'::regclass);


--
-- Name: virtual_wallet_transactions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.virtual_wallet_transactions ALTER COLUMN id SET DEFAULT nextval('public.virtual_wallet_transactions_id_seq'::regclass);


--
-- Name: auth_assessment_records auth_assessment_records_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_assessment_records
    ADD CONSTRAINT auth_assessment_records_pkey PRIMARY KEY (id);


--
-- Name: auth_csrf_challenges auth_csrf_challenges_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_csrf_challenges
    ADD CONSTRAINT auth_csrf_challenges_pkey PRIMARY KEY (nonce_digest);


--
-- Name: auth_login_attempts auth_login_attempts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_login_attempts
    ADD CONSTRAINT auth_login_attempts_pkey PRIMARY KEY (key_digest);


--
-- Name: auth_sessions auth_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_sessions
    ADD CONSTRAINT auth_sessions_pkey PRIMARY KEY (token_digest);


--
-- Name: data_sources data_sources_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_sources
    ADD CONSTRAINT data_sources_name_key UNIQUE (name);


--
-- Name: data_sources data_sources_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_sources
    ADD CONSTRAINT data_sources_pkey PRIMARY KEY (id);


--
-- Name: demo_markets demo_markets_match_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.demo_markets
    ADD CONSTRAINT demo_markets_match_id_key UNIQUE (match_id);


--
-- Name: demo_markets demo_markets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.demo_markets
    ADD CONSTRAINT demo_markets_pkey PRIMARY KEY (id);


--
-- Name: demo_outcomes demo_outcomes_market_id_selection_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.demo_outcomes
    ADD CONSTRAINT demo_outcomes_market_id_selection_key UNIQUE (market_id, selection);


--
-- Name: demo_outcomes demo_outcomes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.demo_outcomes
    ADD CONSTRAINT demo_outcomes_pkey PRIMARY KEY (id);


--
-- Name: external_mappings external_mappings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.external_mappings
    ADD CONSTRAINT external_mappings_pkey PRIMARY KEY (id);


--
-- Name: ingestion_runs ingestion_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ingestion_runs
    ADD CONSTRAINT ingestion_runs_pkey PRIMARY KEY (id);


--
-- Name: leagues leagues_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leagues
    ADD CONSTRAINT leagues_pkey PRIMARY KEY (id);


--
-- Name: match_predictions match_predictions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_predictions
    ADD CONSTRAINT match_predictions_pkey PRIMARY KEY (id);


--
-- Name: matches matches_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_pkey PRIMARY KEY (id);


--
-- Name: model_versions model_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_versions
    ADD CONSTRAINT model_versions_pkey PRIMARY KEY (id);


--
-- Name: season_teams season_teams_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.season_teams
    ADD CONSTRAINT season_teams_pkey PRIMARY KEY (season_id, team_id);


--
-- Name: seasons seasons_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seasons
    ADD CONSTRAINT seasons_pkey PRIMARY KEY (id);


--
-- Name: sports sports_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sports
    ADD CONSTRAINT sports_name_key UNIQUE (name);


--
-- Name: sports sports_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sports
    ADD CONSTRAINT sports_pkey PRIMARY KEY (id);


--
-- Name: sports sports_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sports
    ADD CONSTRAINT sports_slug_key UNIQUE (slug);


--
-- Name: teams teams_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_pkey PRIMARY KEY (id);


--
-- Name: external_mappings uq_external_mappings_provider_entity; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.external_mappings
    ADD CONSTRAINT uq_external_mappings_provider_entity UNIQUE (data_source_id, entity_type, external_id);


--
-- Name: match_predictions uq_match_predictions_match_model; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_predictions
    ADD CONSTRAINT uq_match_predictions_match_model UNIQUE (match_id, model_version_id);


--
-- Name: user_predictions uq_user_predictions_user_match; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_predictions
    ADD CONSTRAINT uq_user_predictions_user_match UNIQUE (user_id, match_id);


--
-- Name: user_predictions user_predictions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_predictions
    ADD CONSTRAINT user_predictions_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: virtual_bets virtual_bets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.virtual_bets
    ADD CONSTRAINT virtual_bets_pkey PRIMARY KEY (id);


--
-- Name: virtual_bets virtual_bets_user_id_request_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.virtual_bets
    ADD CONSTRAINT virtual_bets_user_id_request_key_key UNIQUE (user_id, request_key);


--
-- Name: virtual_wallet_transactions virtual_wallet_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.virtual_wallet_transactions
    ADD CONSTRAINT virtual_wallet_transactions_pkey PRIMARY KEY (id);


--
-- Name: virtual_wallet_transactions virtual_wallet_transactions_user_id_reference_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.virtual_wallet_transactions
    ADD CONSTRAINT virtual_wallet_transactions_user_id_reference_key UNIQUE (user_id, reference);


--
-- Name: virtual_wallets virtual_wallets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.virtual_wallets
    ADD CONSTRAINT virtual_wallets_pkey PRIMARY KEY (user_id);


--
-- Name: idx_ingestion_runs_source_started_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ingestion_runs_source_started_at ON public.ingestion_runs USING btree (data_source_id, started_at DESC);


--
-- Name: idx_match_predictions_match_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_match_predictions_match_id ON public.match_predictions USING btree (match_id);


--
-- Name: idx_matches_away_team_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_matches_away_team_id ON public.matches USING btree (away_team_id);


--
-- Name: idx_matches_home_team_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_matches_home_team_id ON public.matches USING btree (home_team_id);


--
-- Name: idx_matches_league_start_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_matches_league_start_time ON public.matches USING btree (league_id, start_time);


--
-- Name: idx_matches_start_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_matches_start_time ON public.matches USING btree (start_time);


--
-- Name: idx_user_predictions_match_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_predictions_match_id ON public.user_predictions USING btree (match_id);


--
-- Name: idx_user_predictions_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_predictions_user_id ON public.user_predictions USING btree (user_id);


--
-- Name: ix_auth_csrf_challenges_expires_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_csrf_challenges_expires_at ON public.auth_csrf_challenges USING btree (expires_at);


--
-- Name: ix_auth_sessions_expires_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_sessions_expires_at ON public.auth_sessions USING btree (expires_at);


--
-- Name: auth_assessment_records auth_assessment_records_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_assessment_records
    ADD CONSTRAINT auth_assessment_records_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: auth_sessions auth_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_sessions
    ADD CONSTRAINT auth_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: demo_markets demo_markets_match_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.demo_markets
    ADD CONSTRAINT demo_markets_match_id_fkey FOREIGN KEY (match_id) REFERENCES public.matches(id);


--
-- Name: demo_outcomes demo_outcomes_market_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.demo_outcomes
    ADD CONSTRAINT demo_outcomes_market_id_fkey FOREIGN KEY (market_id) REFERENCES public.demo_markets(id);


--
-- Name: external_mappings external_mappings_data_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.external_mappings
    ADD CONSTRAINT external_mappings_data_source_id_fkey FOREIGN KEY (data_source_id) REFERENCES public.data_sources(id);


--
-- Name: ingestion_runs ingestion_runs_data_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ingestion_runs
    ADD CONSTRAINT ingestion_runs_data_source_id_fkey FOREIGN KEY (data_source_id) REFERENCES public.data_sources(id);


--
-- Name: leagues leagues_sport_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leagues
    ADD CONSTRAINT leagues_sport_id_fkey FOREIGN KEY (sport_id) REFERENCES public.sports(id);


--
-- Name: match_predictions match_predictions_match_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_predictions
    ADD CONSTRAINT match_predictions_match_id_fkey FOREIGN KEY (match_id) REFERENCES public.matches(id);


--
-- Name: match_predictions match_predictions_model_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_predictions
    ADD CONSTRAINT match_predictions_model_version_id_fkey FOREIGN KEY (model_version_id) REFERENCES public.model_versions(id);


--
-- Name: match_predictions match_predictions_predicted_winner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_predictions
    ADD CONSTRAINT match_predictions_predicted_winner_id_fkey FOREIGN KEY (predicted_winner_id) REFERENCES public.teams(id);


--
-- Name: matches matches_away_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_away_team_id_fkey FOREIGN KEY (away_team_id) REFERENCES public.teams(id);


--
-- Name: matches matches_home_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_home_team_id_fkey FOREIGN KEY (home_team_id) REFERENCES public.teams(id);


--
-- Name: matches matches_league_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_league_id_fkey FOREIGN KEY (league_id) REFERENCES public.leagues(id);


--
-- Name: matches matches_season_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_season_id_fkey FOREIGN KEY (season_id) REFERENCES public.seasons(id);


--
-- Name: season_teams season_teams_season_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.season_teams
    ADD CONSTRAINT season_teams_season_id_fkey FOREIGN KEY (season_id) REFERENCES public.seasons(id);


--
-- Name: season_teams season_teams_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.season_teams
    ADD CONSTRAINT season_teams_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id);


--
-- Name: seasons seasons_league_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seasons
    ADD CONSTRAINT seasons_league_id_fkey FOREIGN KEY (league_id) REFERENCES public.leagues(id);


--
-- Name: teams teams_sport_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_sport_id_fkey FOREIGN KEY (sport_id) REFERENCES public.sports(id);


--
-- Name: user_predictions user_predictions_match_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_predictions
    ADD CONSTRAINT user_predictions_match_id_fkey FOREIGN KEY (match_id) REFERENCES public.matches(id);


--
-- Name: user_predictions user_predictions_predicted_winner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_predictions
    ADD CONSTRAINT user_predictions_predicted_winner_id_fkey FOREIGN KEY (predicted_winner_id) REFERENCES public.teams(id);


--
-- Name: user_predictions user_predictions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_predictions
    ADD CONSTRAINT user_predictions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: virtual_bets virtual_bets_match_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.virtual_bets
    ADD CONSTRAINT virtual_bets_match_id_fkey FOREIGN KEY (match_id) REFERENCES public.matches(id);


--
-- Name: virtual_bets virtual_bets_outcome_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.virtual_bets
    ADD CONSTRAINT virtual_bets_outcome_id_fkey FOREIGN KEY (outcome_id) REFERENCES public.demo_outcomes(id);


--
-- Name: virtual_bets virtual_bets_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.virtual_bets
    ADD CONSTRAINT virtual_bets_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: virtual_wallet_transactions virtual_wallet_transactions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.virtual_wallet_transactions
    ADD CONSTRAINT virtual_wallet_transactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: virtual_wallets virtual_wallets_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.virtual_wallets
    ADD CONSTRAINT virtual_wallets_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- PostgreSQL database dump complete
--
