-- Additive model pricing evidence tables. Review before explicit setup.

CREATE TABLE model_market_quotes (
	id BIGSERIAL NOT NULL,
	market_id BIGINT NOT NULL,
	quote_key VARCHAR(64) NOT NULL,
	model_version VARCHAR(80) NOT NULL,
	training_end TIMESTAMP WITH TIME ZONE NOT NULL,
	margin NUMERIC(7, 5) NOT NULL,
	probabilities JSON NOT NULL,
	prices JSON NOT NULL,
	features JSON NOT NULL,
	history JSON NOT NULL,
	generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(market_id) REFERENCES demo_markets (id)
)

;
CREATE INDEX ix_model_market_quotes_market_id ON model_market_quotes (market_id);
CREATE INDEX ix_model_market_quotes_quote_key ON model_market_quotes (quote_key);

CREATE TABLE model_bet_quotes (
	bet_id BIGINT NOT NULL,
	quote_id BIGINT NOT NULL,
	PRIMARY KEY (bet_id),
	FOREIGN KEY(bet_id) REFERENCES virtual_bets (id),
	FOREIGN KEY(quote_id) REFERENCES model_market_quotes (id)
)

;
