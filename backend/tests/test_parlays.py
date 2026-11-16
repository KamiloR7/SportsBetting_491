from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from sqlalchemy import select,func,text
from sqlalchemy.orm import Session
from tests.test_virtual_betting import demo,account,payload
from tests.test_model_odds import priced_demo
from app.core.config import settings
from app.database.parlay_tables import initialize_parlays,parlays,legs
from app.database.betting_tables import transactions
from app.services.parlays import combined_return,place_parlay
from app.services.virtual_betting import settle_match
from app.routes.parlays import ParlayRequest


@pytest.fixture
def parlay_demo(priced_demo,monkeypatch):
    client,engine,state=priced_demo
    initialize_parlays(engine)
    monkeypatch.setattr(settings,"PARLAYS_ENABLED",True)
    return client,engine,state


def ticket(client,selection="home",key="parlay-one",stake=100):
    selections=[]
    for match_id,choice in [(1,selection),(2,"home")]:
        market=client.get(f"/matches/{match_id}/markets").json()[0]
        outcome=next(o for o in market["outcomes"] if o["selection"]==choice)
        selections.append({"match_id":match_id,"outcome_id":outcome["id"],"expected_odds":outcome["decimal_odds"]})
    return {"stake":stake,"request_key":key,"legs":selections}


def test_exact_combination_and_whole_point_return():
    assert combined_return(100,["1.47","1.54"])==(Decimal("2.26380000"),226)
    assert combined_return(100,["1.90","1.58"])==(Decimal("3.00200000"),300)
    with pytest.raises(ValueError,match="limit"): combined_return(1_000_000,["1000"]*8)


@pytest.mark.parametrize("first,second,selection,status,credit",[
    ((3,1,False),(3,1,False),"home","WON",300),
    ((1,3,False),(3,1,False),"home","LOST",0),
    ((None,None,True),(3,1,False),"home","WON",158),
    ((None,None,True),(None,None,True),"home","VOID",100),
    ((2,2,False),(3,1,False),"draw","WON",752),
])
def test_parlay_settlement_win_loss_void_and_draw(parlay_demo,first,second,selection,status,credit):
    client,engine,state=parlay_demo;headers=account(client)
    body=ticket(client,selection)
    result=client.post("/parlays",json=body,headers=headers)
    assert result.status_code==201,result.text
    accepted=result.json()
    assert len(accepted["legs"])==2
    assert client.get("/wallet").json()["balance"]==900
    with Session(engine) as db:settle_match(db,1,*first)
    if first[2]:
        current=client.get(f"/parlays/{accepted['id']}").json()
        assert current["current_potential_payout"]==158
    with Session(engine) as db:settle_match(db,2,*second)
    current=client.get(f"/parlays/{accepted['id']}").json()
    assert current["status"]==status
    assert current["actual_payout"]==credit
    assert client.get("/wallet").json()["balance"]==900+credit
    with Session(engine) as db:settle_match(db,1,*first)
    with Session(engine) as db:settle_match(db,2,*second)
    assert client.get("/wallet").json()["balance"]==900+credit
    retry=client.post("/parlays",json=body,headers=headers)
    assert retry.status_code==201,retry.text
    assert retry.json()["id"]==accepted["id"]
    assert client.get("/wallet").json()["balance"]==900+credit
    with Session(engine) as db:
        count=db.execute(select(func.count()).select_from(transactions).where(transactions.c.reference==f"parlay:{accepted['id']}:settlement")).scalar_one()
        assert count==(1 if credit else 0)


def test_duplicate_legs_stale_prices_and_conflicting_retry_are_atomic(parlay_demo):
    client,engine,state=parlay_demo;headers=account(client)
    body=ticket(client)
    duplicate={**body,"legs":[body["legs"][0],body["legs"][0]]}
    assert client.post("/parlays",json=duplicate,headers=headers).status_code==422
    assert client.get("/wallet").json()["balance"]==1000
    state.update(version="test-v2",updated=True)
    assert client.post("/parlays",json=body,headers=headers).status_code==409
    assert client.get("/wallet").json()["balance"]==1000
    with Session(engine) as db:
        assert db.execute(select(func.count()).select_from(parlays)).scalar_one()==0
        assert db.execute(select(func.count()).select_from(legs)).scalar_one()==0
    current=ticket(client)
    first=client.post("/parlays",json=current,headers=headers)
    assert first.status_code==201,first.text
    reordered={**current,"legs":list(reversed(current["legs"]))}
    assert client.post("/parlays",json=reordered,headers=headers).json()["id"]==first.json()["id"]
    assert client.post("/parlays",json={**current,"stake":101},headers=headers).status_code==409
    assert client.get("/wallet").json()["balance"]==900


def test_parlay_owner_csrf_validation_and_closed_match(parlay_demo):
    client,engine,state=parlay_demo;headers=account(client)
    body=ticket(client)
    assert client.post("/parlays",json=body).status_code==403
    assert client.post("/parlays",json={**body,"user_id":999},headers=headers).status_code==422
    assert client.post("/parlays",json={**body,"legs":body["legs"][:1]},headers=headers).status_code==422
    assert client.post("/parlays",json={**body,"stake":1.5},headers=headers).status_code==422
    accepted=client.post("/parlays",json=body,headers=headers).json()
    with Session(engine) as db:settle_match(db,1,3,1)
    assert client.post("/parlays",json={**body,"request_key":"closed"},headers=headers).status_code==409
    account(client,"other-parlay@example.com")
    assert client.get("/parlays").json()==[]
    assert client.get(f"/parlays/{accepted['id']}").status_code==404


def test_accepted_leg_prices_survive_model_repricing(parlay_demo):
    client,engine,state=parlay_demo;headers=account(client)
    body=ticket(client);accepted=client.post("/parlays",json=body,headers=headers).json()
    state.update(version="test-v2",updated=True)
    for match_id in (1,2):assert client.get(f"/matches/{match_id}/markets").status_code==200
    with Session(engine) as db:settle_match(db,1,3,1)
    with Session(engine) as db:settle_match(db,2,3,1)
    stored=client.get(f"/parlays/{accepted['id']}").json()
    assert stored["actual_payout"]==300
    assert client.get("/wallet").json()["balance"]==1200


def test_custom_refill_amount_and_retry_semantics(parlay_demo):
    client,engine,state=parlay_demo;headers=account(client)
    body={"request_key":"custom-137","amount":137}
    assert client.post("/wallet/demo-topup",json=body,headers=headers).json()["balance"]==1137
    assert client.post("/wallet/demo-topup",json=body,headers=headers).json()["balance"]==1137
    assert client.post("/wallet/demo-topup",json={**body,"amount":138},headers=headers).status_code==409
    for amount in (0,-1,1.5,True,1_000_001):
        assert client.post("/wallet/demo-topup",json={"request_key":"invalid","amount":amount},headers=headers).status_code==422
    assert client.get("/wallet").json()["balance"]==1137


def test_concurrent_result_settlement_pays_parlay_once(parlay_demo):
    client,engine,state=parlay_demo
    if engine.dialect.name!="postgresql":pytest.skip("Requires PostgreSQL row locks")
    headers=account(client);accepted=client.post("/parlays",json=ticket(client),headers=headers).json()
    barrier=Barrier(2)
    def finish(match_id):
        with Session(engine) as db:
            db.execute(text("SET LOCAL lock_timeout='8s'"))
            barrier.wait(timeout=5)
            return settle_match(db,match_id,3,1)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(finish,match_id) for match_id in (1,2)]
        for future in futures:future.result(timeout=15)
    assert client.get("/wallet").json()["balance"]==1200
    assert client.get(f"/parlays/{accepted['id']}").json()["status"]=="WON"


def test_concurrent_same_key_placement_debits_once(parlay_demo):
    client,engine,state=parlay_demo
    if engine.dialect.name!="postgresql":pytest.skip("Requires PostgreSQL row locks")
    account(client);user_id=client.get("/auth/me").json()["id"]
    request=ParlayRequest(**ticket(client));barrier=Barrier(2)
    def place():
        with Session(engine) as db:
            db.execute(text("SET LOCAL lock_timeout='8s'"))
            barrier.wait(timeout=5)
            return place_parlay(db,user_id,request)["id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(place) for _ in range(2)]
        ids=[future.result(timeout=15) for future in futures]
    assert len(set(ids))==1
    assert client.get("/wallet").json()["balance"]==900
    with Session(engine) as db:assert db.execute(select(func.count()).select_from(parlays)).scalar_one()==1


PARLAY_PROTECTED=[
    ("GET","/parlays",None),
    ("GET","/parlays/1",None),
    ("POST","/parlays",{"request_key":"denied-ticket","stake":100,"legs":[{"match_id":1,"outcome_id":11,"expected_odds":"1.90"},{"match_id":2,"outcome_id":21,"expected_odds":"1.58"}]}),
]

@pytest.mark.parametrize("method,path,body",PARLAY_PROTECTED)
@pytest.mark.parametrize("state",["anonymous","tampered","expired","logged_out"])
def test_parlay_denials_never_change_points_or_tickets(parlay_demo,method,path,body,state):
    from app.core.authentication import SESSION_COOKIE
    from app.database.auth_tables import sessions
    from app.database.betting_tables import wallets
    client,engine,_=parlay_demo
    if state!="anonymous":
        headers=account(client)
        if state=="tampered":
            token=client.cookies.get(SESSION_COOKIE);client.cookies.clear()
            client.cookies.set(SESSION_COOKIE,token[:-1]+("A" if token[-1]!="A" else "B"))
        elif state=="expired":
            with engine.begin() as conn:conn.execute(sessions.update().values(expires_at=0))
        else:assert client.post("/auth/logout",headers=headers).status_code==204
    def snapshot():
        with engine.connect() as conn:return [conn.execute(select(table)).all() for table in (wallets,transactions,parlays,legs)]
    before=snapshot()
    assert client.request(method,path,json=body).status_code==401
    assert snapshot()==before
