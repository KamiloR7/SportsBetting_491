import io
import json
import os
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import pytest
for key,value in {"DATABASE_HOST":"localhost","DATABASE_PORT":"5432","DATABASE_NAME":"test_db","DATABASE_USER":"test_user","DATABASE_PASSWORD":"test_password"}.items():os.environ.setdefault(key,value)
from fastapi.testclient import TestClient
from app.main import app
from app.routes.standings import cache_dependency
from app.services.standings import normalize_espn,normalize_mlb,fetch_standings,StandingsCache,StandingsUnavailable,MLB_DIVISIONS

NOW=datetime(2026,11,15,12,tzinfo=timezone.utc)

def stat(name,value,display=None):return {"name":name,"value":value,"displayValue":str(value) if display is None else display}

def nfl_payload():
    children=[]
    for group in range(2):
        entries=[]
        for offset in range(16):
            index=group*16+offset;wins=(index*7)%10
            entries.append({"team":{"id":str(index+1),"displayName":f"NFL Team {index}"},"stats":[stat("wins",wins),stat("losses",10-wins),stat("ties",0),stat("winPercent",wins/10,f".{wins}00"),stat("pointsFor",200+index),stat("pointsAgainst",180),stat("pointDifferential",20+index),stat("streak",1,"W1")]})
        children.append({"id":str(group),"name":["AFC","NFC"][group],"abbreviation":["AFC","NFC"][group],"standings":{"season":2026,"seasonDisplayName":"2026","entries":entries}})
    return {"season":{"year":2027},"children":children}

def epl_payload():
    entries=[]
    for index in range(20):
        entries.append({"team":{"id":str(index+1),"displayName":f"EPL Team {index}"},"stats":[stat("wins",5),stat("losses",3),stat("ties",2),stat("gamesPlayed",10),stat("points",-3 if index==19 else 40-index),stat("rank",index+1),stat("pointsFor",12),stat("pointsAgainst",9),stat("pointDifferential",3)]})
    return {"children":[{"id":"1","name":"Premier League","standings":{"season":2026,"seasonDisplayName":"2026-27","entries":entries[::-1]}}]}

def mlb_payload(season=2026):
    records=[]
    for group,division_id in enumerate(MLB_DIVISIONS):
        entries=[]
        for index in range(5):
            total=group*5+index
            entries.append({"team":{"id":total+1,"name":f"MLB Team {total}"},"season":str(season),"wins":60+total,"losses":102-total,"winningPercentage":f"{(60+total)/162:.3f}","divisionRank":str(5-index),"leagueRank":str(15-total%15),"sportRank":str(30-total),"runsScored":700+total,"runsAllowed":650-total,"runDifferential":50+2*total,"divisionGamesBack":str(4-index),"leagueGamesBack":str(14-total%15),"sportGamesBack":str(29-total),"streak":{"streakCode":"W1"}})
        records.append({"division":{"id":division_id},"teamRecords":entries})
    return {"records":records}


def test_nfl_conferences_and_overall_use_full_provider_records():
    source=nfl_payload();data=normalize_espn("NFL",source,NOW)
    assert data["season"]=="2026"  # Not the root's future-season label.
    assert [len(group["rows"]) for group in data["groups"]]==[16,16]
    assert [row["team"]["id"] for row in data["groups"][0]["rows"]]==[str(i+1) for i in range(16)]
    percentages=[row["sort_pct"] for row in data["overall"]]
    assert percentages==sorted(percentages,reverse=True)
    assert [row["overall_position"] for row in data["overall"]]==list(range(1,33))
    assert data["team_count"]==32 and data["views"]==["conference","overall"]


def test_epl_preserves_rank_points_and_deductions():
    data=normalize_espn("EPL",epl_payload(),NOW)
    rows=data["groups"][0]["rows"]
    assert [row["provider_rank"] for row in rows]==list(range(1,21))
    assert rows[-1]["stats"]["points"]=="-3"
    assert rows[0]["stats"]["points"]=="40"  # Do not recompute 3W+D.
    assert data["season_label"]=="2026-27"


def test_mlb_divisions_leagues_overall_and_contextual_games_behind():
    data=normalize_mlb(mlb_payload(),2026,NOW)
    assert len([g for g in data["groups"] if g["kind"]=="division"])==6
    assert [len(g["rows"]) for g in data["groups"] if g["kind"]=="league"]==[15,15]
    assert len(data["overall"])==30 and data["overall"][0]["overall_rank"]==1
    top=data["groups"][0]["rows"][0]
    assert top["provider_rank"]==1
    assert top["stats"]["gb_division"]=="0" and top["stats"]["gb_overall"]=="25"


def test_incomplete_duplicate_and_mixed_season_payloads_are_rejected():
    incomplete=nfl_payload();incomplete["children"][0]["standings"]["entries"].pop()
    with pytest.raises(StandingsUnavailable):normalize_espn("NFL",incomplete,NOW)
    duplicate=nfl_payload();duplicate["children"][1]["standings"]["entries"][0]["team"]["id"]="1"
    with pytest.raises(StandingsUnavailable):normalize_espn("NFL",duplicate,NOW)
    mixed=nfl_payload();mixed["children"][1]["standings"]["season"]=2025
    with pytest.raises(StandingsUnavailable):normalize_espn("NFL",mixed,NOW)
    with pytest.raises(StandingsUnavailable):normalize_mlb(mlb_payload(2025),2026,NOW)
    bad_pct=nfl_payload();bad_pct["children"][0]["standings"]["entries"][0]["stats"]=[item for item in bad_pct["children"][0]["standings"]["entries"][0]["stats"] if item["name"]!="winPercent"]
    with pytest.raises(StandingsUnavailable):normalize_espn("NFL",bad_pct,NOW)
    missing_rank=mlb_payload();missing_rank["records"][0]["teamRecords"][0].pop("sportRank")
    with pytest.raises(StandingsUnavailable):normalize_mlb(missing_rank,2026,NOW)


def test_mlb_selects_latest_season_with_played_games():
    urls=[]
    def opener(url,timeout):
        urls.append(url);assert timeout==12
        data={"records":[]} if "season=2026" in url else mlb_payload(2025)
        return io.BytesIO(json.dumps(data).encode())
    data=fetch_standings("MLB",opener,NOW)
    assert data["season"]=="2025" and len(urls)==2
    assert "season=2025" in data["source_url"]


def test_cache_ttl_stale_fallback_retry_throttling_and_disk_reuse(tmp_path):
    clock=[NOW];calls=[];offline=[False]
    def fetch(league):
        calls.append(league)
        if offline[0]:raise OSError("offline")
        return normalize_espn(league,nfl_payload(),clock[0])
    cache=StandingsCache(tmp_path,fetch,lambda:clock[0])
    first=cache.get("NFL");first["groups"][0]["rows"][0]["stats"]["wins"]="999"
    assert cache.get("NFL")["groups"][0]["rows"][0]["stats"]["wins"]!="999" and len(calls)==1
    reloaded=StandingsCache(tmp_path,lambda league:(_ for _ in ()).throw(AssertionError("Fresh disk cache should be used")),lambda:clock[0])
    assert reloaded.get("NFL")["stale"] is False
    clock[0]+=timedelta(minutes=6);offline[0]=True
    stale=cache.get("NFL")
    assert stale["stale"] is True and stale["retrieved_at"]==NOW.isoformat()
    assert cache.get("NFL")["stale"] is True and len(calls)==2
    clock[0]+=timedelta(seconds=61);offline[0]=False
    assert cache.get("NFL")["stale"] is False and len(calls)==3


def test_cache_without_saved_data_returns_unavailable_and_throttles(tmp_path):
    calls=[]
    def fail(league):calls.append(league);raise OSError("offline")
    cache=StandingsCache(tmp_path,fail,lambda:NOW)
    for _ in range(2):
        with pytest.raises(StandingsUnavailable):cache.get("NFL")
    assert len(calls)==1
    with pytest.raises(StandingsUnavailable):cache.get("../secret")


def test_standings_endpoint_is_public_and_restricts_leagues():
    class FakeCache:
        def get(self,league):return normalize_espn(league,nfl_payload(),NOW)
    app.dependency_overrides[cache_dependency]=lambda:FakeCache()
    try:
        with TestClient(app) as client:
            result=client.get("/standings/NFL")
            assert result.status_code==200 and result.json()["team_count"]==32
            assert client.get("/standings/NBA").status_code==422
    finally:app.dependency_overrides.pop(cache_dependency,None)
