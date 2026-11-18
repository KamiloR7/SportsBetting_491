"""Import verified downloaded historical sources without synthetic fixtures.
Run from backend: python -m app.database.import_real_history
"""
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
from sqlalchemy import text
from app.database.refresh_real_matches import apply_snapshot, FEEDS

EPL_NAMES={"Bournemouth":"AFC Bournemouth","Brighton":"Brighton & Hove Albion","Man City":"Manchester City","Man United":"Manchester United","Newcastle":"Newcastle United","Nott'm Forest":"Nottingham Forest","Tottenham":"Tottenham Hotspur","West Ham":"West Ham United","Wolves":"Wolverhampton Wanderers","Luton":"Luton Town","Ipswich":"Ipswich Town","Leicester":"Leicester City","Leeds":"Leeds United","Southampton":"Southampton"}
NFL_ABBR={"LA":"LAR","WAS":"WSH","JAC":"JAX"}

def build_snapshot(raw, engine):
    manifest=json.loads((raw/"provenance.json").read_text())
    with engine.connect() as conn:
        nfl={r.abbreviation:r.name for r in conn.execute(text("SELECT t.abbreviation,t.name FROM teams t JOIN leagues l ON l.sport_id=t.sport_id WHERE l.abbreviation='NFL'"))}
    snapshot={"source":"historical provider files", "retrieved_at":manifest["retrieved_at_utc"],"matches":[]}
    for league,entry in manifest["sports"].items():
        dataset=raw/f"{league.lower()}_games.csv"
        if hashlib.sha256(dataset.read_bytes()).hexdigest()!=entry["dataset_sha256"]: raise ValueError("Dataset checksum mismatch")
        allowed=set(pd.read_csv(dataset,dtype={"game_id":str}).game_id)
        for i,source in enumerate(entry["sources"]):
            payload=(raw/f"{league.lower()}_source_{i}.bin").read_bytes()
            if hashlib.sha256(payload).hexdigest()!=source["sha256"]: raise ValueError("Source checksum mismatch")
            if league=="MLB":
                games=[g for day in json.loads(payload)["dates"] for g in day["games"] if str(g["gamePk"]) in allowed and g["status"]["detailedState"] in ("Final","Game Over","Completed Early") and all("score" in g["teams"][side] for side in ("home","away"))]
                records=[]
                for game in games:
                    row={"game_id":str(game["gamePk"]),"source":"MLB Stats API","season":int(game["season"]),"kickoff_utc":game["gameDate"],"neutral_site":False}
                    for side in ("home","away"):
                        team=game["teams"][side]
                        row.update({f"{side}_team_id":str(team["team"]["id"]),f"{side}_team_name":team["team"]["name"],f"{side}_team_abbr":None,f"{side}_score":int(team["score"])})
                    records.append(row)
            else:
                records=[]; table=pd.read_csv(io.BytesIO(payload))
                for item in table.to_dict("records"):
                    if league=="NFL":
                        if str(item["game_id"]) not in allowed: continue
                        local=datetime.fromisoformat(f"{item['gameday']}T{item['gametime']}").replace(tzinfo=ZoneInfo("America/New_York"))
                        row={"game_id":str(item["game_id"]),"source":"nflverse","season":int(item["season"]),"kickoff_utc":local.astimezone(timezone.utc).isoformat(),"neutral_site":item.get("location")=="Neutral"}
                        for side in ("home","away"):
                            abbr=NFL_ABBR.get(item[f"{side}_team"],item[f"{side}_team"])
                            if abbr not in nfl: raise ValueError(f"Unmapped NFL team {abbr}")
                            row.update({f"{side}_team_id":str(item[f"{side}_team"]),f"{side}_team_name":nfl[abbr],f"{side}_team_abbr":abbr,f"{side}_score":int(item[f"{side}_score"])})
                    else:
                        if item.get("Div")!="E0" or pd.isna(item.get("FTHG")) or pd.isna(item.get("FTAG")): continue
                        if pd.isna(item.get("Time")): raise ValueError("Missing historical EPL kickoff time")
                        date=pd.to_datetime(item["Date"],dayfirst=True).date(); local=datetime.fromisoformat(f"{date}T{item['Time']}").replace(tzinfo=ZoneInfo("Europe/London"))
                        season=int("20"+source["url"].split("/")[-2][:2])
                        row={"game_id":f"{date}:{item['HomeTeam']}:{item['AwayTeam']}","source":"football-data.co.uk","season":season,"kickoff_utc":local.astimezone(timezone.utc).isoformat(),"neutral_site":False}
                        for side,key,score in (("home","HomeTeam","FTHG"),("away","AwayTeam","FTAG")):
                            name=EPL_NAMES.get(item[key],item[key]);row.update({f"{side}_team_id":str(item[key]),f"{side}_team_name":name,f"{side}_team_abbr":None,f"{side}_score":int(item[score])})
                    records.append(row)
            for row in records:
                row.update({"league":league,"sport":FEEDS[league][1],"status":"completed"});snapshot["matches"].append(row)
    return snapshot

def main():
    from app.database.db import engine
    raw=Path(__file__).resolve().parents[3]/"data/raw"
    snapshot=build_snapshot(raw,engine)
    print(f"Validated {len(snapshot['matches'])} historical records",flush=True)
    result=apply_snapshot(snapshot,engine)
    output=raw.parents[1]/"build/history-import.json"
    output.write_text(json.dumps({"count":len(result),"sources":json.loads((raw/"provenance.json").read_text())["sports"]},indent=2))
    print(f"Historical import complete: {len(result)} records")

if __name__=="__main__": main()
