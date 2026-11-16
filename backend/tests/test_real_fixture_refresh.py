import pytest
from app.database.refresh_real_matches import normalize

def event(state="pre", completed=False):
    return {"season":{"year":2026},"events":[{"id":"100", "competitions":[{"date":"2026-11-20T20:00:00Z", "status":{"type":{"state":state,"completed":completed}}, "competitors":[{"homeAway":side,"score":score,"team":{"id":identifier,"displayName":name,"abbreviation":name}} for side,score,identifier,name in [("home","2","1","AAA"),("away","1","2","BBB")]]}]}]}

def test_scheduled_scores_are_not_used():
    row=normalize(event(),"EPL")[0]
    assert row["home_score"] is None and row["away_score"] is None
    assert row["status"]=="scheduled" and row["game_id"]=="EPL:100"
    assert row["home_team_id"]=="EPL:1"

def test_completed_result_is_preserved():
    row=normalize(event("post",True),"NFL")[0]
    assert (row["home_score"],row["away_score"],row["status"])==(2,1,"completed")

def test_missing_kickoff_timezone_rejected():
    data=event();data["events"][0]["competitions"][0]["date"]="2026-11-20T20:00:00"
    with pytest.raises(ValueError,match="timezone"): normalize(data,"MLB")
