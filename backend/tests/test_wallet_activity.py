from sqlalchemy import select, func
from sqlalchemy.orm import Session
from tests.test_virtual_betting import demo, account, payload
from tests.test_model_odds import priced_demo
from tests.test_parlays import parlay_demo, ticket
from app.database.betting_tables import transactions, wallets
from app.services.virtual_betting import settle_match
from app.services.wallet_activity import describe_activity


def test_wallet_links_single_and_parlay_stakes_then_winning_returns(parlay_demo):
    client,engine,_=parlay_demo;headers=account(client)
    single=client.post("/bets",json=payload(expected_odds="1.90"),headers=headers).json()
    parlay=client.post("/parlays",json=ticket(client),headers=headers).json()
    rows=client.get("/wallet/transactions").json()
    stake=next(row for row in rows if row["kind"]=="STAKE")
    assert stake["ticket_type"]=="single" and stake["ticket_id"]==single["id"]
    assert stake["ticket_status"]=="PENDING" and stake["source_label"].startswith("To single bet #")
    assert "EPL Home vs EPL Away" in stake["description"] and "1.90" in stake["description"]
    combined=next(row for row in rows if row["kind"]=="PARLAY_STAKE")
    assert combined["ticket_type"]=="parlay" and combined["ticket_id"]==parlay["id"]
    assert "2-leg parlay" in combined["source_label"] and "NFL Home" in combined["description"]
    with Session(engine) as db:settle_match(db,1,3,1)
    with Session(engine) as db:settle_match(db,2,3,1)
    rows=client.get("/wallet/transactions").json()
    credit=next(row for row in rows if row["kind"]=="PAYOUT")
    assert credit["title"]=="Winning bet payout" and credit["amount"]==190
    assert credit["ticket_status"]=="WON" and credit["source_label"].startswith("From single bet #")
    assert "Return includes the original stake" in credit["description"]
    parlay_credit=next(row for row in rows if row["kind"]=="PARLAY_PAYOUT")
    assert parlay_credit["title"]=="Winning parlay payout" and parlay_credit["amount"]==300
    assert parlay_credit["ticket_status"]=="WON"
    assert client.get("/wallet").json()["balance"]==1290
    assert client.get("/wallet/transactions").json()==rows


def test_non_ticket_credits_have_clear_sources_and_no_ticket_link(demo):
    client,engine=demo;headers=account(client)
    assert client.post("/wallet/demo-topup",json={"request_key":"custom","amount":137},headers=headers).status_code==200
    rows=client.get("/wallet/transactions").json()
    topup=next(row for row in rows if row["kind"]=="DEMO_TOPUP")
    assert topup["title"]=="Demo points added" and "137" in topup["description"]
    assert topup["ticket_id"] is None
    initial=next(row for row in rows if row["kind"]=="INITIAL")
    assert initial["source_label"]=="From account setup"
    assert client.post("/wallet/demo-reset",json={"request_key":"new-round","confirmation":"RESET"},headers=headers).status_code==200
    reset=client.get("/wallet/transactions").json()[0]
    assert reset["title"]=="Demo wallet reset" and reset["ticket_id"] is None


def test_ticket_metadata_cannot_expand_another_users_bet(demo):
    client,engine=demo;headers=account(client,"owner-activity@example.com")
    other=client.post("/bets",json=payload(),headers=headers).json()
    account(client,"reader-activity@example.com")
    reader_id=client.get("/auth/me").json()["id"]
    with Session(engine) as db:
        before=db.execute(select(func.count()).select_from(transactions)).scalar_one()
        decorated=describe_activity(db,reader_id,[{"id":999,"kind":"STAKE","amount":-100,"reference":f"bet:{other['id']}:stake"}])[0]
        assert decorated["ticket_id"] is None and decorated["ticket_type"] is None
        assert "Home" not in decorated["description"]
        assert db.execute(select(func.count()).select_from(transactions)).scalar_one()==before
    assert all(row["ticket_id"] is None for row in client.get("/wallet/transactions").json())
