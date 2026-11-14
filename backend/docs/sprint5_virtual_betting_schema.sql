-- Review-only additive schema preview. Not applied.
-- The setup CLI checks for existing tables; this preview does not.
-- Existing users and matches tables are prerequisites.

CREATE TABLE auth_sessions (
	token_digest VARCHAR(64) NOT NULL,
	user_id BIGINT NOT NULL,
	csrf_token VARCHAR(43) NOT NULL,
	expires_at FLOAT NOT NULL,
	PRIMARY KEY (token_digest),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_auth_sessions_expires_at ON auth_sessions (expires_at);

CREATE TABLE auth_csrf_challenges (
	nonce_digest VARCHAR(64) NOT NULL,
	csrf_token VARCHAR(43) NOT NULL,
	expires_at FLOAT NOT NULL,
	PRIMARY KEY (nonce_digest)
);

CREATE INDEX ix_auth_csrf_challenges_expires_at ON auth_csrf_challenges (expires_at);

CREATE TABLE auth_login_attempts (
	key_digest VARCHAR(64) NOT NULL,
	window_start FLOAT NOT NULL,
	failure_count INTEGER NOT NULL,
	blocked_until FLOAT NOT NULL,
	failure_times JSON DEFAULT '[]' NOT NULL,
	PRIMARY KEY (key_digest)
);

CREATE TABLE auth_assessment_records (
	id BIGSERIAL NOT NULL,
	owner_id BIGINT NOT NULL,
	note TEXT NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE virtual_wallets (
	user_id BIGINT NOT NULL,
	balance INTEGER NOT NULL,
	PRIMARY KEY (user_id),
	CHECK (balance >= 0),
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE demo_markets (
	id BIGSERIAL NOT NULL,
	match_id BIGINT NOT NULL,
	is_open BOOLEAN DEFAULT true NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (match_id),
	FOREIGN KEY(match_id) REFERENCES matches (id)
);

CREATE TABLE demo_outcomes (
	id BIGSERIAL NOT NULL,
	market_id BIGINT NOT NULL,
	selection VARCHAR(10) NOT NULL,
	decimal_odds NUMERIC(9, 4) NOT NULL,
	PRIMARY KEY (id),
	CHECK (selection IN ('home','draw','away')),
	CHECK (decimal_odds > 1 AND decimal_odds <= 1000),
	UNIQUE (market_id, selection),
	FOREIGN KEY(market_id) REFERENCES demo_markets (id)
);

CREATE TABLE virtual_bets (
	id BIGSERIAL NOT NULL,
	user_id BIGINT NOT NULL,
	match_id BIGINT NOT NULL,
	outcome_id BIGINT NOT NULL,
	selection VARCHAR(10) NOT NULL,
	stake INTEGER NOT NULL,
	accepted_odds NUMERIC(9, 4) NOT NULL,
	potential_payout INTEGER NOT NULL,
	status VARCHAR(10) DEFAULT 'PENDING' NOT NULL,
	request_key VARCHAR(100) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	CHECK (stake > 0),
	CHECK (potential_payout >= stake),
	CHECK (status IN ('PENDING','WON','LOST','VOID')),
	UNIQUE (user_id, request_key),
	FOREIGN KEY(user_id) REFERENCES users (id),
	FOREIGN KEY(match_id) REFERENCES matches (id),
	FOREIGN KEY(outcome_id) REFERENCES demo_outcomes (id)
);

CREATE TABLE virtual_wallet_transactions (
	id BIGSERIAL NOT NULL,
	user_id BIGINT NOT NULL,
	amount INTEGER NOT NULL,
	kind VARCHAR(20) NOT NULL,
	reference VARCHAR(120) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	UNIQUE (user_id, reference),
	FOREIGN KEY(user_id) REFERENCES users (id)
);
