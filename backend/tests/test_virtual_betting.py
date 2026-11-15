"""Real API/auth/SQL transactions against a disposable file database."""
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
from sqlalchemy.engine import make_url
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text, insert, select
from sqlalchemy.orm import Session

for key,value in {'DATABASE_HOST':'localhost','DATABASE_PORT':'5432','DATABASE_NAME':'test_db','DATABASE_USER':'test_user','DATABASE_PASSWORD':'test_password'}.items():
    os.environ.setdefault(key,value)
from app.main import app
from app.core.config import settings
from app.core.authentication import SESSION_COOKIE
from app.database.db import get_db
from app.database.auth_tables import users, initialize_auth_tables
from app.database.betting_tables import initialize_betting_tables, markets, outcomes, wallets, transactions
from app.services.virtual_betting import settle_match

@pytest.fixture(params=['sqlite', 'postgres'])
def demo(request, tmp_path, monkeypatch):
    bootstrap = None
    schema = None
    if request.param == 'postgres':
        value = os.getenv('SPRINT5_TEST_DATABASE_URL')
        if not value or os.getenv('SPRINT5_ALLOW_DISPOSABLE_TEST') != '1':
            pytest.skip('Explicit disposable PostgreSQL test database not configured')
        url = make_url(value)
        if url.get_backend_name() != 'postgresql' or url.database != 'sportsbetting_sprint5_test' or url.host not in {'localhost','127.0.0.1','::1'}:
            pytest.fail('Only local sportsbetting_sprint5_test is allowed')
        schema = 'betting_s5_' + uuid4().hex
        bootstrap = create_engine(url)
        with bootstrap.begin() as conn:
            conn.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
        engine = create_engine(url, connect_args={'options': f'-csearch_path={schema}'})
    else:
        engine=create_engine('sqlite:///'+str(tmp_path/'betting.sqlite'),connect_args={'check_same_thread':False})
    users.create(engine)
    initialize_auth_tables(engine)
    with engine.begin() as c:
        c.execute(text('CREATE TABLE leagues (id INTEGER PRIMARY KEY, abbreviation TEXT, name TEXT, sport_id INTEGER)'))
        c.execute(text('CREATE TABLE teams (id INTEGER PRIMARY KEY, name TEXT, sport_id INTEGER)'))
        c.execute(text('CREATE TABLE matches (id '+('SERIAL' if engine.dialect.name=='postgresql' else 'INTEGER')+' PRIMARY KEY, league_id INTEGER, home_team_id INTEGER, away_team_id INTEGER, start_time TIMESTAMP, status TEXT, home_score INTEGER, away_score INTEGER, neutral_site BOOLEAN DEFAULT false)'))
        c.execute(text("INSERT INTO teams VALUES (1,'EPL Home',1),(2,'EPL Away',1),(3,'NFL Home',2),(4,'NFL Away',2),(5,'MLB Home',3),(6,'MLB Away',3)"))
        for i,league in enumerate(['EPL','NFL','MLB'],1):
            c.execute(text('INSERT INTO leagues VALUES (:id,:league,:league,:id)'),{'id':i,'league':league})
            c.execute(text("INSERT INTO matches (id,league_id,home_team_id,away_team_id,start_time,status) VALUES (:id,:id,:home,:away,:start,'scheduled')"),{'id':i,'home':i*2-1,'away':i*2,'start':datetime.now(timezone.utc)+timedelta(days=1)})
    if engine.dialect.name == 'postgresql':
        with engine.begin() as c:
            c.execute(text("SELECT setval(pg_get_serial_sequence('matches','id'),3)"))
    initialize_betting_tables(engine)
    with engine.begin() as c:
        for i in [1,2,3]:
            c.execute(insert(markets).values(id=i,match_id=i,is_open=True))
            for offset,selection in enumerate(['home','away']+(['draw'] if i==1 else []),1):
                c.execute(insert(outcomes).values(id=i*10+offset,market_id=i,selection=selection,decimal_odds=Decimal('2.5')))
    if engine.dialect.name == 'postgresql':
        with engine.begin() as c:
            # Explicit fixture IDs do not advance PostgreSQL sequences.
            for table in ['demo_markets', 'demo_outcomes']:
                c.execute(text(f"SELECT setval(pg_get_serial_sequence('{table}','id'), (SELECT MAX(id) FROM {table}))"))
    monkeypatch.setattr(settings,'VIRTUAL_BETTING_ENABLED',True)
    def database():
        with Session(engine) as db: yield db
    previous=app.dependency_overrides.copy()
    app.dependency_overrides[get_db]=database
    with TestClient(app,base_url='https://testserver') as client:
        yield client,engine
    app.dependency_overrides.clear(); app.dependency_overrides.update(previous)
    engine.dispose()
    if bootstrap is not None:
        with bootstrap.begin() as conn:
            conn.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
        bootstrap.dispose()


def account(client,email='demo@example.com'):
    r=client.post('/auth/register',json={'email':email,'password':'SyntheticPass123!'})
    assert r.status_code==201,r.text
    client.cookies.delete(SESSION_COOKIE)
    token=client.get('/auth/csrf').json()['csrf_token']
    r=client.post('/auth/login',json={'email':email,'password':'SyntheticPass123!'},headers={'X-CSRF-Token':token})
    assert r.status_code==200,r.text
    return {'X-CSRF-Token':client.get('/auth/csrf').json()['csrf_token']}


def payload(**changes):
    return {'match_id':1,'outcome_id':11,'stake':100,'expected_odds':'2.5','request_key':'bet-1',**changes}

@pytest.mark.parametrize('match_id',[1,2,3])
def test_workflow_persistence_and_duplicate_settlement(demo,match_id):
    client,engine=demo; headers=account(client)
    assert client.get('/auth/me').status_code==200
    assert client.get('/wallet').json()['balance']==1000
    match=client.get(f'/matches/{match_id}')
    assert match.status_code==200,match.text
    assert match.json()['id']==match_id
    available=client.get(f'/matches/{match_id}/markets').json()
    assert len(available[0]['outcomes'])==(3 if match_id==1 else 2)
    body=payload(match_id=match_id,outcome_id=match_id*10+1)
    response=client.post('/bets',json=body,headers=headers)
    assert response.status_code==201,response.text
    bet=response.json(); assert bet['potential_payout']==250 and bet['status']=='PENDING'
    assert client.get('/wallet').json()['balance']==900
    assert client.post('/bets',json=body,headers=headers).json()['id']==bet['id']
    assert client.get('/wallet').json()['balance']==900
    with Session(engine) as db: assert settle_match(db,match_id,3,1)['settled']==1
    assert client.get(f"/bets/{bet['id']}").json()['status']=='WON'
    assert client.get('/wallet').json()['balance']==1150
    with Session(engine) as db: assert settle_match(db,match_id,3,1)['settled']==0
    engine.dispose() # force a new database connection, retaining persisted state
    with TestClient(app,base_url='https://testserver') as restarted:
        restarted.cookies.update(client.cookies)
        assert restarted.get('/wallet').json()['balance']==1150
        assert restarted.get('/bets').json()[0]['status']=='WON'
    assert client.post('/auth/logout',headers=headers).status_code==204
    assert client.get('/wallet').status_code==401

@pytest.mark.parametrize('change,status',[
    ({'stake':1001},409),({'stake':0},422),({'stake':1.5},422),({'stake':True},422),
    ({'expected_odds':'1'},422),({'expected_odds':'3'},409),({'expected_odds':'NaN'},422),
    ({'outcome_id':999},422),({'match_id':999},404)])
def test_invalid_bets_do_not_change_points(demo,change,status):
    client,engine=demo; headers=account(client)
    assert client.post('/bets',json=payload(**change),headers=headers).status_code==status
    assert client.get('/wallet').json()['balance']==1000
    assert client.get('/bets').json()==[]

@pytest.mark.parametrize('scores,void,expected,balance', [((0,1),False,'LOST',900),((1,1),False,'LOST',900),((None,None),True,'VOID',1000)])
def test_loss_and_void(demo,scores,void,expected,balance):
    client,engine=demo; headers=account(client)
    assert client.post('/bets',json=payload(),headers=headers).status_code==201
    with Session(engine) as db: settle_match(db,1,*scores,void=void)
    assert client.get('/bets').json()[0]['status']==expected
    assert client.get('/wallet').json()['balance']==balance
    with Session(engine) as db: assert settle_match(db,1,*scores,void=void)['settled']==0


def test_draw_topup_ownership_and_retry_conflict(demo):
    client,engine=demo; headers=account(client)
    bet=client.post('/bets',json=payload(outcome_id=13),headers=headers).json()
    assert client.post('/bets',json=payload(stake=101),headers=headers).status_code==409
    with Session(engine) as db: settle_match(db,1,2,2)
    assert client.get('/wallet').json()['balance']==1150
    assert client.post('/wallet/demo-topup',json={'request_key':'refill1'},headers=headers).json()['balance']==2150
    assert client.post('/wallet/demo-topup',json={'request_key':'refill1'},headers=headers).json()['balance']==2150
    assert len(client.get('/wallet/transactions').json())==4
    account(client,'other@example.com')
    assert client.get('/bets').json()==[]
    assert client.get(f"/bets/{bet['id']}").status_code==404
    assert client.get('/wallet').json()['balance']==1000


def test_closed_match_and_invalid_login(demo):
    client,engine=demo; headers=account(client)
    with engine.begin() as c: c.execute(text("UPDATE matches SET status='final' WHERE id=1"))
    assert client.post('/bets',json=payload(),headers=headers).status_code==409
    client.cookies.delete(SESSION_COOKIE)
    token=client.get('/auth/csrf').json()['csrf_token']
    assert client.post('/auth/login',json={'email':'demo@example.com','password':'wrong'},headers={'X-CSRF-Token':token}).status_code==401
    assert client.post('/bets',json=payload()).status_code==401
    assert client.post('/auth/register',json={'email':'demo@example.com','password':'SyntheticPass123!'}).status_code==409

@pytest.mark.parametrize('match_id',[2,3])
def test_two_way_tie_refunds(demo,match_id):
    client,engine=demo; headers=account(client)
    assert client.post('/bets',json=payload(match_id=match_id,outcome_id=match_id*10+1),headers=headers).status_code==201
    with Session(engine) as db: settle_match(db,match_id,1,1)
    assert client.get('/bets').json()[0]['status']=='VOID'
    assert client.get('/wallet').json()['balance']==1000


def test_failure_rolls_back_bet_and_deduction(demo):
    client,engine=demo
    if engine.dialect.name!='sqlite': pytest.skip('SQLite fault injection trigger')
    headers=account(client)
    with engine.begin() as c:
        c.execute(text("CREATE TRIGGER fail_stake BEFORE INSERT ON virtual_wallet_transactions WHEN NEW.kind='STAKE' BEGIN SELECT RAISE(ABORT,'synthetic failure'); END"))
    with pytest.raises(Exception,match='synthetic failure'):
        client.post('/bets',json=payload(),headers=headers)
    assert client.get('/wallet').json()['balance']==1000
    assert client.get('/bets').json()==[]


def test_past_match_rejected(demo):
    client,engine=demo; headers=account(client)
    with engine.begin() as c:
        c.execute(text('UPDATE matches SET start_time=:start WHERE id=1'),{'start':datetime.now(timezone.utc)-timedelta(days=1)})
    assert client.post('/bets',json=payload(),headers=headers).status_code==409
    assert client.get('/wallet').json()['balance']==1000


@pytest.mark.parametrize('same_key',[True,False])
def test_postgres_concurrent_requests(demo,same_key):
    from concurrent.futures import ThreadPoolExecutor
    from fastapi import HTTPException
    from app.routes.virtual_betting import BetRequest
    from app.services.virtual_betting import place_bet
    client,engine=demo
    if engine.dialect.name!='postgresql': pytest.skip('Requires PostgreSQL row locks')
    account(client)
    user_id=client.get('/auth/me').json()['id']
    def place(key):
        with Session(engine) as db:
            try:
                result=place_bet(db,user_id,BetRequest(**payload(stake=100 if same_key else 600,request_key=key)))
                return result['id']
            except HTTPException as exc:
                assert exc.status_code==409
                return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(place,['concurrent-1','concurrent-1' if same_key else 'concurrent-2']))
    if same_key: assert results[0]==results[1] and results[0] is not None
    else: assert sum(value is not None for value in results)==1
    assert client.get('/wallet').json()['balance']==(900 if same_key else 400)
    assert len(client.get('/bets').json())==1


def test_synthetic_fixture_command(demo):
    from app.database.virtual_demo_fixtures import create_demo_fixtures
    client,engine=demo
    with Session(engine) as db: rows=create_demo_fixtures(db)
    assert [row['league'] for row in rows]==['EPL','NFL','MLB']
    for row in rows:
        market=client.get(f"/matches/{row['match_id']}/markets").json()[0]
        assert market['odds_source']=='synthetic_demo'
        assert len(market['outcomes'])==(3 if row['league']=='EPL' else 2)


def test_local_http_demo_flow(demo):
    from app.core.authentication import SESSION_COOKIE
    if not settings.LOCAL_DEMO_HTTP: pytest.skip('Run separately with LOCAL_DEMO_HTTP=true')
    _,engine=demo
    with TestClient(app,base_url='http://127.0.0.1:8000') as client:
        headers={'Origin':'http://127.0.0.1:5173'}
        assert client.post('/auth/register',json={'email':'local@example.com','password':'SyntheticPass123!'}).status_code==201
        csrf=client.get('/auth/csrf',headers=headers)
        assert csrf.status_code==200,csrf.text
        headers['X-CSRF-Token']=csrf.json()['csrf_token']
        login=client.post('/auth/login',json={'email':'local@example.com','password':'SyntheticPass123!'},headers=headers)
        assert login.status_code==200,login.text
        assert SESSION_COOKIE=='vigor_session'
        assert client.cookies.get(SESSION_COOKIE)
        assert client.get('/wallet').json()['balance']==1000
        headers['X-CSRF-Token']=client.get('/auth/csrf',headers=headers).json()['csrf_token']
        assert client.post('/bets',json=payload(),headers=headers).status_code==201
        assert client.get('/wallet').json()['balance']==900
        assert client.post('/auth/logout',headers=headers).status_code==204
    with TestClient(app,base_url='http://public.example.com') as remote:
        assert remote.get('/auth/me').status_code==403

BETTING_PROTECTED = [
    ('GET','/wallet',None), ('GET','/wallet/transactions',None),
    ('POST','/wallet/demo-topup',{'request_key':'denied-refill'}),
    ('POST','/bets',payload()), ('GET','/bets',None), ('GET','/bets/1',None),
]

@pytest.mark.parametrize('method,path,body',BETTING_PROTECTED)
@pytest.mark.parametrize('state',['anonymous','tampered','expired','logged_out'])
def test_betting_denies_invalid_sessions_without_point_changes(demo,method,path,body,state):
    from app.database.auth_tables import sessions
    from app.database.betting_tables import bets
    client,engine=demo
    if state!='anonymous':
        headers=account(client)
        if state=='tampered':
            token=client.cookies.get(SESSION_COOKIE)
            client.cookies.clear()
            client.cookies.set(SESSION_COOKIE,token[:-1]+('A' if token[-1]!='A' else 'B'))
        elif state=='expired':
            with engine.begin() as c: c.execute(sessions.update().values(expires_at=0))
        else:
            assert client.post('/auth/logout',headers=headers).status_code==204
    def snapshot():
        with engine.connect() as c:
            return [c.execute(select(table)).all() for table in [wallets,transactions,bets]]
    before=snapshot()
    assert client.request(method,path,json=body).status_code==401
    assert snapshot()==before


def settlement_snapshot(engine):
    """Capture only disposable fixture records to prove rejection/rollback safety."""
    from app.database.betting_tables import bets
    with engine.connect() as connection:
        return {
            table.name: connection.execute(select(table).order_by(*table.primary_key.columns)).all()
            for table in [wallets, transactions, bets, markets]
        } | {'matches': connection.execute(text('SELECT * FROM matches ORDER BY id')).all()}


def mark_external_result(engine, match_id, home=None, away=None, cancelled=False):
    with engine.begin() as connection:
        connection.execute(
            text('UPDATE matches SET status=:status, home_score=:home, away_score=:away WHERE id=:id'),
            {'status': 'cancelled' if cancelled else 'final', 'home': home, 'away': away, 'id': match_id},
        )


@pytest.mark.parametrize('match_id,selection,scores,expected,stake', [
    (1, 'home', (3, 1), 'WON', 101),
    (1, 'away', (3, 1), 'LOST', 100),
    (1, 'draw', (2, 2), 'WON', 100),
    (2, 'home', (1, 1), 'VOID', 100),
    (3, 'away', (1, 1), 'VOID', 100),
])
def test_external_final_pending_settlement(demo, match_id, selection, scores, expected, stake):
    client, engine = demo
    headers = account(client)
    outcome = next(row for row in client.get(f'/matches/{match_id}/markets').json()[0]['outcomes']
                   if row['selection'] == selection)
    placed = client.post('/bets', json=payload(match_id=match_id, outcome_id=outcome['id'], stake=stake), headers=headers)
    assert placed.status_code == 201, placed.text
    bet = placed.json()
    # Future changes to market odds must not change the accepted payout snapshot.
    with engine.begin() as connection:
        connection.execute(outcomes.update().where(outcomes.c.id == outcome['id']).values(decimal_odds=Decimal('9.0')))
    mark_external_result(engine, match_id, *scores)
    with engine.connect() as connection:
        original_result = connection.execute(text('SELECT * FROM matches WHERE id=:id'), {'id': match_id}).one()
    with Session(engine) as db:
        assert settle_match(db, match_id, *scores) == {'match_id': match_id, 'settled': 1}
    expected_credit = bet['potential_payout'] if expected == 'WON' else (stake if expected == 'VOID' else 0)
    assert client.get('/wallet').json()['balance'] == 1000 - stake + expected_credit
    assert client.get(f"/bets/{bet['id']}").json()['status'] == expected
    ledger = client.get('/wallet/transactions').json()
    credits = [row for row in ledger if row['reference'] == f"bet:{bet['id']}:settlement"]
    assert len(credits) == (1 if expected_credit else 0)
    if credits:
        assert credits[0]['amount'] == expected_credit
        assert credits[0]['kind'] == ('PAYOUT' if expected == 'WON' else 'REFUND')
    with engine.connect() as connection:
        assert connection.execute(text('SELECT * FROM matches WHERE id=:id'), {'id': match_id}).one() == original_result
        assert not connection.execute(select(markets.c.is_open).where(markets.c.match_id == match_id)).scalar_one()
    completed = settlement_snapshot(engine)
    with Session(engine) as db:
        assert settle_match(db, match_id, *scores)['settled'] == 0
    assert settlement_snapshot(engine) == completed


def test_external_cancelled_pending_settlement(demo):
    client, engine = demo
    headers = account(client)
    assert client.post('/bets', json=payload(), headers=headers).status_code == 201
    # Preserve provider-supplied metadata even if cancellation includes partial scores.
    mark_external_result(engine, 1, 1, 0, cancelled=True)
    original = settlement_snapshot(engine)['matches']
    with Session(engine) as db:
        assert settle_match(db, 1, void=True)['settled'] == 1
    assert client.get('/wallet').json()['balance'] == 1000
    assert client.get('/bets').json()[0]['status'] == 'VOID'
    assert settlement_snapshot(engine)['matches'] == original
    completed = settlement_snapshot(engine)
    with Session(engine) as db:
        assert settle_match(db, 1, void=True)['settled'] == 0
    assert settlement_snapshot(engine) == completed


@pytest.mark.parametrize('stored,requested,void,cancelled', [
    ((3, 1), (1, 3), False, False),  # Conflicting winner.
    ((3, 1), (4, 1), False, False),  # Score correction, even with same winner.
    ((3, 1), (None, None), False, False),
    ((3, 1), (-1, 1), False, False),
    ((3, 1), (True, 1), False, False),
    ((None, None), (3, 1), False, False),  # Stored final result is incomplete.
    ((3, 1), (None, None), True, False),  # Cannot turn final into cancellation.
    ((None, None), (3, 1), False, True),  # Cancellation requires explicit void.
])
def test_external_result_rejection_is_unchanged(demo, stored, requested, void, cancelled):
    client, engine = demo
    headers = account(client)
    assert client.post('/bets', json=payload(), headers=headers).status_code == 201
    mark_external_result(engine, 1, *stored, cancelled=cancelled)
    before = settlement_snapshot(engine)
    with pytest.raises(ValueError), Session(engine) as db:
        settle_match(db, 1, *requested, void=void)
    assert settlement_snapshot(engine) == before


def test_external_final_preserves_already_settled_bet(demo):
    from app.database.betting_tables import bets
    client, engine = demo
    headers = account(client)
    first = client.post('/bets', json=payload(request_key='first'), headers=headers).json()
    second = client.post('/bets', json=payload(request_key='second'), headers=headers).json()
    # Simulate one previously settled bet alongside a still-pending bet.
    with engine.begin() as connection:
        connection.execute(bets.update().where(bets.c.id == first['id']).values(status='WON'))
        connection.execute(wallets.update().values(balance=wallets.c.balance + first['potential_payout']))
        connection.execute(insert(transactions).values(user_id=first['user_id'], amount=first['potential_payout'],
                           kind='PAYOUT', reference=f"bet:{first['id']}:settlement"))
        first_before = connection.execute(select(bets).where(bets.c.id == first['id'])).one()
        credit_before = connection.execute(select(transactions).where(transactions.c.reference == f"bet:{first['id']}:settlement")).one()
    mark_external_result(engine, 1, 3, 1)
    with Session(engine) as db:
        assert settle_match(db, 1, 3, 1)['settled'] == 1
    assert client.get('/wallet').json()['balance'] == 1300
    assert client.get(f"/bets/{second['id']}").json()['status'] == 'WON'
    with engine.connect() as connection:
        assert connection.execute(select(bets).where(bets.c.id == first['id'])).one() == first_before
        assert connection.execute(select(transactions).where(transactions.c.reference == f"bet:{first['id']}:settlement")).one() == credit_before
    assert len(client.get('/wallet/transactions').json()) == 5


def test_external_settlement_failure_rolls_back(demo):
    from sqlalchemy import event
    client, engine = demo
    headers = account(client)
    assert client.post('/bets', json=payload(), headers=headers).status_code == 201
    mark_external_result(engine, 1, 3, 1)
    before = settlement_snapshot(engine)

    def fail_after_payout(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith('UPDATE DEMO_MARKETS'):
            raise RuntimeError('Synthetic failure after payout and bet status writes')

    event.listen(engine, 'before_cursor_execute', fail_after_payout)
    try:
        with pytest.raises(RuntimeError, match='Synthetic failure'), Session(engine) as db:
            settle_match(db, 1, 3, 1)
    finally:
        event.remove(engine, 'before_cursor_execute', fail_after_payout)
    assert settlement_snapshot(engine) == before
    with Session(engine) as db:
        assert settle_match(db, 1, 3, 1)['settled'] == 1
    assert client.get('/wallet').json()['balance'] == 1150


@pytest.mark.parametrize('external_final', [True, False])
@pytest.mark.parametrize('conflicting', [False, True])
def test_postgres_concurrent_settlement(demo, external_final, conflicting):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    client, engine = demo
    if engine.dialect.name != 'postgresql':
        pytest.skip('Settlement concurrency requires PostgreSQL row locks')
    headers = account(client)
    assert client.post('/bets', json=payload(request_key='home'), headers=headers).status_code == 201
    assert client.post('/bets', json=payload(outcome_id=12, request_key='away'), headers=headers).status_code == 201
    if external_final:
        mark_external_result(engine, 1, 3, 1)
    barrier = Barrier(2)

    def settle(scores):
        with Session(engine) as db:
            barrier.wait(timeout=10)
            try:
                return ('ok', settle_match(db, 1, *scores)['settled'])
            except ValueError as exc:
                assert str(exc) == 'Match already settled with a different result.'
                return ('conflict', 0)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(settle, [(3, 1), (1, 3) if conflicting else (3, 1)]))
    assert sum(count for status, count in results if status == 'ok') == 2
    assert sum(status == 'conflict' for status, _ in results) == (1 if conflicting else 0)
    if not conflicting:
        assert sorted(count for _, count in results) == [0, 2]
    history = client.get('/bets').json()
    assert sorted(row['status'] for row in history) == ['LOST', 'WON']
    ledger = client.get('/wallet/transactions').json()
    payouts = [row for row in ledger if row['kind'] == 'PAYOUT']
    assert len(ledger) == 4 and len(payouts) == 1 and payouts[0]['amount'] == 250
    assert len({row['reference'] for row in ledger}) == len(ledger)
    assert client.get('/wallet').json()['balance'] == sum(row['amount'] for row in ledger) == 1050
    with engine.connect() as connection:
        stored = connection.execute(text('SELECT home_score,away_score FROM matches WHERE id=1')).one()
        winner = 'home' if stored.home_score > stored.away_score else 'away'
        assert next(row for row in history if row['selection'] == winner)['status'] == 'WON'
        assert not connection.execute(select(markets.c.is_open).where(markets.c.match_id == 1)).scalar_one()
