from decimal import Decimal
from types import SimpleNamespace
from datetime import datetime, timezone
import pytest
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from tests.test_virtual_betting import demo, account, payload
from app.core.config import settings
from app.database.model_odds_tables import initialize_model_odds, quotes, bet_quotes
from app.services.model_odds import decimal_prices
from app.services.virtual_betting import settle_match
from app.services.prediction_service import MatchHistoryRepository


def test_decimal_prices_reflect_probabilities_and_margin():
    assert decimal_prices({"home":0.6,"away":0.4}) == {"home":Decimal("1.58"),"away":Decimal("2.38")}
    assert decimal_prices({"home":0.5,"away":0.5},0) == {"home":Decimal("2.00"),"away":Decimal("2.00")}
    priced=decimal_prices({"home":0.5,"draw":0.2,"away":0.3})
    assert priced["home"] < priced["away"] < priced["draw"]
    assert sum(Decimal(1)/v for v in priced.values()) > Decimal("1.05")


@pytest.mark.parametrize("probabilities,margin",[({"home":0,"away":1},.05),({"home":float("nan"),"away":.4},.05),({"home":.6,"away":.6},.05),({"home":.5,"away":.5},-.01),({"home":.5,"away":.5},.3)])
def test_invalid_prices_are_rejected(probabilities,margin):
    with pytest.raises(ValueError): decimal_prices(probabilities,margin)


@pytest.fixture
def priced_demo(demo,monkeypatch):
    client,engine=demo
    initialize_model_odds(engine)
    monkeypatch.setattr(settings,"MODEL_ODDS_ENABLED",True)
    monkeypatch.setattr(settings,"MODEL_ODDS_MARGIN",.05)
    state={"version":"test-v1","updated":False,"fail":False}
    class Registry:
        def get(self,sport): return None,{"artifact_version":state["version"],"train_end":"2020-01-01T00:00:00+00:00"}
        def predict(self,context):
            if state["fail"]: raise ValueError("Missing model")
            if context.sport=="EPL": probabilities={"home":.6,"draw":.2,"away":.2} if state["updated"] else {"home":.5,"draw":.2,"away":.3}
            else: probabilities={"home":.7,"away":.3} if state["updated"] else {"home":.6,"away":.4}
            return probabilities,self.get(context.sport)[1]
    monkeypatch.setattr("app.services.model_odds.configured_registry",lambda:Registry())
    def context(self,match_id):
        return SimpleNamespace(sport={1:"EPL",2:"NFL",3:"MLB"}[match_id],feature_cutoff=datetime.now(timezone.utc),features={"home_win_rate":.5},home_history_games=100,away_history_games=100)
    monkeypatch.setattr(MatchHistoryRepository,"get_context",context)
    return client,engine,state


@pytest.mark.parametrize("match_id",[1,2,3])
def test_model_quote_is_locked_for_settlement_even_after_repricing(priced_demo,match_id):
    client,engine,state=priced_demo
    headers=account(client)
    market=client.get(f"/matches/{match_id}/markets").json()[0]
    assert market["odds_source"]=="model_derived"
    assert set(market["probabilities"])==({"home","draw","away"} if match_id==1 else {"home","away"})
    home=next(o for o in market["outcomes"] if o["selection"]=="home")
    old_odds=Decimal(home["decimal_odds"])
    body=payload(match_id=match_id,outcome_id=home["id"],expected_odds=str(old_odds))
    response=client.post("/bets",json=body,headers=headers)
    assert response.status_code==201,response.text
    original=response.json()
    assert original["odds_source"]=="model_derived"
    assert client.get("/wallet").json()["balance"]==900
    with Session(engine) as db:
        assert db.execute(select(func.count()).select_from(bet_quotes)).scalar_one()==1
    state.update(version="test-v2",updated=True)
    changed=client.get(f"/matches/{match_id}/markets").json()[0]
    assert changed["model_version"]=="test-v2"
    assert Decimal(next(o for o in changed["outcomes"] if o["selection"]=="home")["decimal_odds"])!=old_odds
    assert Decimal(client.get(f"/bets/{original['id']}").json()["accepted_odds"])==old_odds
    with Session(engine) as db: assert settle_match(db,match_id,3,1)["settled"]==1
    assert client.get("/wallet").json()["balance"]==900+original["potential_payout"]
    with Session(engine) as db: assert settle_match(db,match_id,3,1)["settled"]==0
    assert client.post("/bets",json=body,headers=headers).json()["id"]==original["id"]
    assert client.get("/wallet").json()["balance"]==900+original["potential_payout"]


def test_stale_odds_rejected_without_debit(priced_demo):
    client,engine,state=priced_demo;headers=account(client)
    market=client.get("/matches/1/markets").json()[0]
    home=next(o for o in market["outcomes"] if o["selection"]=="home")
    state.update(version="test-v2",updated=True)
    result=client.post("/bets",json=payload(outcome_id=home["id"],expected_odds=home["decimal_odds"]),headers=headers)
    assert result.status_code==409,result.text
    assert client.get("/wallet").json()["balance"]==1000
    assert client.get("/bets").json()==[]


def test_unavailable_model_never_falls_back_to_fixed_prices(priced_demo):
    client,engine,state=priced_demo;headers=account(client);state["fail"]=True
    assert client.get("/matches/1/markets").status_code==503
    assert client.post("/bets",json=payload(),headers=headers).status_code==503
    assert client.get("/wallet").json()["balance"]==1000


def test_identical_reads_reuse_quote(priced_demo):
    client,engine,state=priced_demo
    first=client.get("/matches/1/markets").json()[0]
    second=client.get("/matches/1/markets").json()[0]
    assert first==second
    with Session(engine) as db: assert db.execute(select(func.count()).select_from(quotes)).scalar_one()==1


def test_forecast_exposes_same_three_way_probabilities_used_for_pricing():
    from app.services.prediction_service import PredictionService, MatchContext
    class Repository:
        def get_context(self,match_id):
            return MatchContext(match_id=match_id,sport="EPL",home_team_id=1,home_team_name="Home",away_team_id=2,away_team_name="Away",features={},home_history_games=20,away_history_games=20)
    class Registry:
        def predict(self,context): return {"home":.4,"draw":.35,"away":.25},{"artifact_version":"three-way-test"}
    forecast=PredictionService(None,Repository(),market_models=Registry()).predict(42)
    assert forecast.outcome_probabilities=={"home":.4,"draw":.35,"away":.25}
    assert forecast.market_outcome=="home"
    assert forecast.probabilities.home_win==.4
    assert forecast.probabilities.not_home_win==.6


def test_extreme_valid_probabilities_produce_bounded_prices():
    prices=decimal_prices({"home":1e-100,"draw":.6,"away":.4})
    assert prices["home"]==Decimal("1000.00")
    assert all(Decimal("1.01")<=value<=Decimal("1000.00") for value in prices.values())
