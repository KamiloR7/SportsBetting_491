-- Additive schema preview only. Use setup_parlays against an authorized local database.


CREATE TABLE virtual_parlays (
	id BIGSERIAL NOT NULL,
	user_id BIGINT NOT NULL,
	stake INTEGER NOT NULL,
	combined_odds NUMERIC(20, 8) NOT NULL,
	potential_payout INTEGER NOT NULL,
	actual_payout INTEGER,
	status VARCHAR(10) DEFAULT 'PENDING' NOT NULL,
	request_key VARCHAR(100) NOT NULL,
	request_fingerprint VARCHAR(64) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
	settled_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	UNIQUE (user_id, request_key),
	CHECK (stake > 0),
	CHECK (potential_payout >= stake),
	CHECK (status IN ('PENDING','WON','LOST','VOID')),
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;

CREATE INDEX ix_virtual_parlays_user_id ON virtual_parlays (user_id);


CREATE TABLE virtual_parlay_legs (
	id BIGSERIAL NOT NULL,
	parlay_id BIGINT NOT NULL,
	match_id BIGINT NOT NULL,
	outcome_id BIGINT NOT NULL,
	quote_id BIGINT NOT NULL,
	selection VARCHAR(10) NOT NULL,
	accepted_odds NUMERIC(9, 4) NOT NULL,
	status VARCHAR(10) DEFAULT 'PENDING' NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (parlay_id, match_id),
	CHECK (accepted_odds > 1 AND accepted_odds <= 1000),
	CHECK (selection IN ('home','away','draw')),
	CHECK (status IN ('PENDING','WON','LOST','VOID')),
	FOREIGN KEY(parlay_id) REFERENCES virtual_parlays (id),
	FOREIGN KEY(match_id) REFERENCES matches (id),
	FOREIGN KEY(outcome_id) REFERENCES demo_outcomes (id),
	FOREIGN KEY(quote_id) REFERENCES model_market_quotes (id)
)

;

CREATE INDEX ix_virtual_parlay_legs_match_id ON virtual_parlay_legs (match_id);

CREATE INDEX ix_virtual_parlay_legs_parlay_id ON virtual_parlay_legs (parlay_id);
