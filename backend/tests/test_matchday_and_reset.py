from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier
import pytest
from sqlalchemy import text, select
from sqlalchemy.orm import Session
from tests.test_virtual_betting import demo, account, payload
from tests.test_model_odds import priced_demo
from tests.test_parlays import parlay_demo, ticket
from app.services.virtual_betting import settle_match
from app.services.demo_reset import reset_demo
from app.database.betting_tables import transactions, wallets


def test_matchday_excludes_old_games_and_sorts_before_pagination(demo):
    client, engine = demo
    data = [(1,"2026-11-15T18:00:00+00:00","in_progress"), (2,"2026-11-15T08:00:00+00:00","final"),
            (3,"2026-11-15T23:00:00+00:00","scheduled"), (4,"2026-11-17T18:00:00+00:00","scheduled"),
            (5,"2023-11-15T18:00:00+00:00","final"), (6,"2023-11-15T18:00:00+00:00","in_progress"),
            (7,"2026-11-16T08:00:00+00:00","final"), (8,"2026-11-15T07:59:59+00:00","final"),
            (9,"2026-11-15T20:00:00+00:00","postponed")]
    with engine.begin() as conn:
        for mid,start,status in data:
            values={"id":mid,"start":datetime.fromisoformat(start),"status":status}
            if mid<=3:conn.execute(text("UPDATE matches SET league_id=1,start_time=:start,status=:status WHERE id=:id"),values)
            else:conn.execute(text("INSERT INTO matches(id,league_id,home_team_id,away_team_id,start_time,status) VALUES(:id,1,1,2,:start,:status)"),values)
    params={"league_id":1,"view":"matchday","day_start":"2026-11-15T00:00:00-08:00","day_end":"2026-11-16T00:00:00-08:00"}
    result=client.get("/matches",params=params)
    assert result.status_code==200,result.text
    assert [m["id"] for m in result.json()]==[1,2,9,3,4]
    assert [m["id"] for m in client.get("/matches",params={**params,"limit":2,"offset":2}).json()]==[9,3]
    assert 5 in [m["id"] for m in client.get("/matches",params={"league_id":1,"status":"final"}).json()]
    for invalid in ({"day_start":"2026-11-15T00:00:00"},{"day_end":"2026-12-16T00:00:00-08:00"},{"status":"final"}):
        assert client.get("/matches",params={**params,**invalid}).status_code==422
    assert client.get("/matches",params={"view":"matchday"}).status_code==422


def test_reset_clears_own_tickets_preserves_other_user_and_retries(parlay_demo):
    client,engine,_=parlay_demo
    other_headers=account(client,"other-reset@example.com")
    other_id=client.get("/auth/me").json()["id"]
    other_parlay=client.post("/parlays",json=ticket(client,key="other"),headers=other_headers)
    assert other_parlay.status_code==201,other_parlay.text
    headers=account(client,"reset-owner@example.com")
    own_id=client.get("/auth/me").json()["id"]
    single=client.post("/bets",json=payload(expected_odds="1.90"),headers=headers)
    assert single.status_code==201,single.text
    assert client.post("/parlays",json=ticket(client),headers=headers).status_code==201
    body={"request_key":"reset-one","confirmation":"RESET"}
    assert client.post("/wallet/demo-reset",json=body).status_code==403
    assert client.post("/wallet/demo-reset",json={"request_key":"no-confirm"},headers=headers).status_code==422
    assert client.post("/wallet/demo-reset",json={**body,"user_id":other_id},headers=headers).status_code==422
    reset=client.post("/wallet/demo-reset",json=body,headers=headers)
    assert reset.status_code==200,reset.text
    assert reset.json()["balance"]==1000
    assert client.get("/bets").json()==[]
    assert client.get("/parlays").json()==[]
    assert client.get(f"/bets/{single.json()['id']}").status_code==404
    assert [row["kind"] for row in client.get("/wallet/transactions").json()]==["DEMO_RESET"]
    assert client.post("/wallet/demo-topup",json={"amount":10,"request_key":"after"},headers=headers).status_code==200
    assert client.post("/wallet/demo-reset",json=body,headers=headers).json()["balance"]==1010
    with Session(engine) as db:settle_match(db,1,3,1)
    with Session(engine) as db:settle_match(db,2,3,1)
    assert client.get("/wallet").json()["balance"]==1010
    with engine.connect() as conn:
        assert conn.execute(select(wallets.c.balance).where(wallets.c.user_id==other_id)).scalar_one()==1200
    assert client.post("/wallet/demo-reset",json={**body,"request_key":"reset-two"},headers=headers).json()["balance"]==1000
    assert len(client.get("/wallet/transactions").json())==1
    # Replaying an older reset does not remove new-round points.
    assert client.post("/wallet/demo-topup",json={"amount":11,"request_key":"new-round"},headers=headers).status_code==200
    assert client.post("/wallet/demo-reset",json=body,headers=headers).json()["balance"]==1011


def test_reset_and_settlement_concurrency_has_no_late_payout(parlay_demo):
    client,engine,_=parlay_demo
    if engine.dialect.name!="postgresql":pytest.skip("Requires PostgreSQL row locks")
    headers=account(client);user_id=client.get("/auth/me").json()["id"]
    assert client.post("/parlays",json=ticket(client),headers=headers).status_code==201
    barrier=Barrier(2)
    def reset():
        with Session(engine) as db:
            db.execute(text("SET LOCAL lock_timeout='8s'"));barrier.wait(timeout=5)
            reset_demo(db,user_id,"race-reset")
    def settle():
        with Session(engine) as db:
            db.execute(text("SET LOCAL lock_timeout='8s'"));barrier.wait(timeout=5)
            settle_match(db,1,3,1)
        with Session(engine) as db:settle_match(db,2,3,1)
    with ThreadPoolExecutor(max_workers=2) as pool:
        tasks=[pool.submit(reset),pool.submit(settle)]
        for task in tasks:task.result(timeout=20)
    assert client.get("/wallet").json()["balance"]==1000
    assert client.get("/parlays").json()==[]
