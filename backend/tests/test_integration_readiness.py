"""Clean-clone setup and handoff verification in isolated PostgreSQL schemas."""
import os
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

for name, value in {
    'DATABASE_HOST': 'localhost', 'DATABASE_PORT': '5432',
    'DATABASE_NAME': 'test_db', 'DATABASE_USER': 'test_user',
    'DATABASE_PASSWORD': 'test_password',
}.items():
    os.environ.setdefault(name, value)

from app.core.config import Settings, settings
from app.database import setup_virtual_betting
from app.database.db import get_db
from app.database.seed_data import seed_leagues, seed_sports, seed_teams
from app.database.virtual_demo_fixtures import create_demo_fixtures
from app.main import app
from app.services.virtual_betting import settle_match


@pytest.fixture
def empty_postgres():
    value = os.getenv('SPRINT5_TEST_DATABASE_URL')
    if not value or os.getenv('SPRINT5_ALLOW_DISPOSABLE_TEST') != '1':
        pytest.skip('Explicit disposable PostgreSQL test database not configured')
    url = make_url(value)
    if (url.get_backend_name() != 'postgresql' or url.database != 'sportsbetting_sprint5_test'
            or url.host not in {'localhost', '127.0.0.1', '::1'} or url.query):
        pytest.fail('Only local sportsbetting_sprint5_test without URL overrides is allowed')
    schema = 'readiness_s5_' + uuid4().hex
    bootstrap = create_engine(url)
    engine = None
    try:
        with bootstrap.begin() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
        engine = create_engine(url, connect_args={'options': f'-csearch_path={schema}'})
        yield engine
    finally:
        if engine is not None:
            engine.dispose()
        with bootstrap.begin() as connection:
            connection.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        bootstrap.dispose()


def apply_base(engine, legacy=False, password_definition=None):
    sql = (Path(__file__).parents[1] / 'app/database/sports_prediction_schema.sql').read_text()
    if legacy:
        line = '    password_hash VARCHAR(255) NOT NULL,\n'
        assert line in sql
        sql = sql.replace(line, '')
    elif password_definition is not None:
        sql = sql.replace('password_hash VARCHAR(255) NOT NULL', 'password_hash ' + password_definition)
    with engine.begin() as connection:
        connection.exec_driver_sql(sql.replace('BEGIN;', '').replace('COMMIT;', ''))


def schema_signature(engine):
    inspector = inspect(engine)
    return {
        table: (inspector.get_columns(table), inspector.get_pk_constraint(table),
                inspector.get_foreign_keys(table), inspector.get_unique_constraints(table),
                inspector.get_check_constraints(table), inspector.get_indexes(table))
        for table in inspector.get_table_names()
    }


def reference_seed(engine):
    with engine.begin() as connection:
        sports = seed_sports(connection)
        seed_leagues(connection, sports)
        seed_teams(connection, sports)


def test_clean_setup_cli_and_repeat_preserve_schema(empty_postgres, monkeypatch):
    from app.database import virtual_betting_cli
    apply_base(empty_postgres)
    monkeypatch.setattr(virtual_betting_cli, 'engine', empty_postgres)
    monkeypatch.setattr('sys.argv', ['virtual_betting_cli', 'setup'])
    virtual_betting_cli.main()
    before = schema_signature(empty_postgres)
    sequences = inspect(empty_postgres).get_sequence_names()
    assert len(sequences) == 17
    virtual_betting_cli.main()
    after = schema_signature(empty_postgres)
    # Reflected TypeEngine instances compare by identity; normalize their rendering.
    assert repr(before) == repr(after)
    assert len(after) == 22
    assert inspect(empty_postgres).get_sequence_names() == sequences
    with empty_postgres.connect() as connection:
        assert connection.execute(text('SELECT COUNT(*) FROM users')).scalar_one() == 0
        assert connection.execute(text('SELECT COUNT(*) FROM virtual_wallets')).scalar_one() == 0
        assert connection.execute(text('SELECT COUNT(*) FROM virtual_bets')).scalar_one() == 0


def test_setup_rejects_incomplete_base_before_writes(empty_postgres):
    with pytest.raises(ValueError, match='Base schema is incomplete'):
        setup_virtual_betting.initialize_virtual_betting(empty_postgres)
    assert inspect(empty_postgres).get_table_names() == []


@pytest.mark.parametrize('password_definition', [None, 'VARCHAR(255)', 'TEXT NOT NULL'])
def test_setup_rejects_legacy_users_before_writes(empty_postgres, password_definition):
    apply_base(empty_postgres, legacy=password_definition is None, password_definition=password_definition)
    before = repr(schema_signature(empty_postgres))
    with pytest.raises(ValueError, match='migration'):
        setup_virtual_betting.initialize_virtual_betting(empty_postgres)
    assert set(inspect(empty_postgres).get_table_names()) == setup_virtual_betting.BASE_TABLES
    assert repr(schema_signature(empty_postgres)) == before


def test_setup_ddl_rolls_back_as_one_transaction(empty_postgres, monkeypatch):
    apply_base(empty_postgres)

    def unavailable(connection):
        raise RuntimeError('Synthetic setup failure')

    monkeypatch.setattr(setup_virtual_betting, 'initialize_betting_tables', unavailable)
    with pytest.raises(RuntimeError, match='Synthetic setup failure'):
        setup_virtual_betting.initialize_virtual_betting(empty_postgres)
    assert set(inspect(empty_postgres).get_table_names()) == setup_virtual_betting.BASE_TABLES


def test_required_settings_and_default_flags(monkeypatch):
    required = ['DATABASE_HOST', 'DATABASE_PORT', 'DATABASE_NAME', 'DATABASE_USER', 'DATABASE_PASSWORD']
    for key in required + ['LOCAL_DEMO_HTTP', 'VIRTUAL_BETTING_ENABLED', 'AUTH_ASSESSMENT_ENABLED']:
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None)
    assert {entry['loc'][0] for entry in error.value.errors()} == set(required)
    configured = Settings(_env_file=None, DATABASE_HOST='localhost', DATABASE_PORT=5432,
                          DATABASE_NAME='synthetic_test', DATABASE_USER='synthetic', DATABASE_PASSWORD='synthetic')
    assert not configured.LOCAL_DEMO_HTTP
    assert not configured.VIRTUAL_BETTING_ENABLED
    assert not configured.AUTH_ASSESSMENT_ENABLED


def test_clean_schema_seed_and_api_handoff(empty_postgres, monkeypatch):
    apply_base(empty_postgres)
    setup_virtual_betting.initialize_virtual_betting(empty_postgres)
    reference_seed(empty_postgres)
    with empty_postgres.connect() as connection:
        before = connection.execute(text('SELECT COUNT(*) FROM teams')).scalar_one()
    reference_seed(empty_postgres)
    with empty_postgres.connect() as connection:
        assert connection.execute(text('SELECT COUNT(*) FROM teams')).scalar_one() == before
    with Session(empty_postgres) as db:
        fixtures = create_demo_fixtures(db)
    monkeypatch.setattr(settings, 'VIRTUAL_BETTING_ENABLED', True)

    def database():
        with Session(empty_postgres) as db:
            yield db

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = database
    try:
        with TestClient(app, base_url='https://testserver') as client:
            documented = client.get('/openapi.json').json()['paths']
            assert {'/auth/register', '/auth/login', '/auth/logout', '/auth/me', '/auth/csrf',
                    '/wallet', '/wallet/transactions', '/wallet/demo-topup', '/matches',
                    '/matches/{match_id}/markets', '/bets', '/bets/{bet_id}',
                    '/predictions', '/predictions/matches/{match_id}'} <= set(documented)
            for path in ['/health', '/sports', '/leagues', '/teams', '/matches', '/matches/history']:
                assert client.get(path).status_code == 200
            assert len(client.get('/matches').json()) == 3
            assert client.post('/auth/register', json={
                'email': 'readiness@example.com', 'password': 'SyntheticPassword123!'}).status_code == 201
            challenge = client.get('/auth/csrf').json()['csrf_token']
            assert client.post('/auth/login', json={'email': 'readiness@example.com',
                'password': 'SyntheticPassword123!'}, headers={'X-CSRF-Token': challenge}).status_code == 200
            csrf = {'X-CSRF-Token': client.get('/auth/csrf').json()['csrf_token']}
            assert client.get('/auth/me').status_code == 200
            assert client.get('/wallet').json()['balance'] == 1000
            match_id = fixtures[0]['match_id']
            assert client.get(f'/matches/{match_id}').json()['id'] == match_id
            outcome = client.get(f'/matches/{match_id}/markets').json()[0]['outcomes'][0]
            response = client.post('/bets', json={'match_id': match_id, 'outcome_id': outcome['id'],
                'stake': 100, 'expected_odds': outcome['decimal_odds'], 'request_key': 'readiness-bet'}, headers=csrf)
            assert response.status_code == 201, response.text
            bet_id = response.json()['id']
            assert client.get('/wallet').json()['balance'] == 900
            assert client.get(f'/bets/{bet_id}').json()['status'] == 'PENDING'
            assert len(client.get('/bets').json()) == 1
            # Simulate Data Engineering's already-final update, without a collector.
            with empty_postgres.begin() as connection:
                connection.execute(text('UPDATE matches SET status=\'final\', home_score=3, away_score=1 WHERE id=:id'), {'id': match_id})
            with Session(empty_postgres) as db:
                assert settle_match(db, match_id, 3, 1)['settled'] == 1
            assert client.get('/wallet').json()['balance'] == 1150
            assert client.get(f'/bets/{bet_id}').json()['status'] == 'WON'
            assert len(client.get('/wallet/transactions').json()) == 3
            # Refill is existing behavior: validate the integration contract once.
            for _ in range(2):
                assert client.post('/wallet/demo-topup', json={'request_key': 'readiness-refill'}, headers=csrf).json()['balance'] == 2150
            assert client.post('/auth/logout', headers=csrf).status_code == 204
            assert client.get('/wallet').status_code == 401
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
