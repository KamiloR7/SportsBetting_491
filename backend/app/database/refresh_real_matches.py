"""Fetch ESPN fixtures to a reviewable snapshot; apply explicitly to a local database.

No synthetic fixtures are inserted. Model pricing replaces legacy seed prices when enabled.
Existing provider match IDs are preserved by the project's upsert service.
"""
import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen

FEEDS = {"NFL": ("football/nfl", "American Football"), "MLB": ("baseball/mlb", "Baseball"), "EPL": ("soccer/eng.1", "Soccer")}

def normalize(payload, league):
    rows=[]
    for event in payload.get("events", []):
        competition=event["competitions"][0]
        sides={c["homeAway"]:c for c in competition["competitors"]}
        if set(sides)!={"home","away"}: raise ValueError("Invalid competitor sides")
        status=competition["status"]["type"]
        name=status.get("name", "")
        if name in {"STATUS_CANCELED", "STATUS_CANCELLED"}: state="cancelled"
        elif name in {"STATUS_POSTPONED", "STATUS_DELAYED"}: state="postponed"
        elif status.get("completed"): state="completed"
        elif status.get("state")=="pre": state="scheduled"
        elif status.get("state")=="in": state="in_progress"
        else: continue
        kickoff=datetime.fromisoformat(competition["date"].replace("Z","+00:00"))
        if kickoff.tzinfo is None: raise ValueError("Missing kickoff timezone")
        row={"game_id":f"{league}:{event['id']}", "source":"ESPN", "sport":FEEDS[league][1], "league":league,
             "kickoff_utc":kickoff.isoformat(), "status":state, "season":int(event.get("season",payload.get("season",{}))["year"]),
             "neutral_site":bool(competition.get("neutralSite",False))}
        for side,c in sides.items():
            team=c["team"]
            row.update({f"{side}_team_id":f"{league}:{team['id']}", f"{side}_team_name":team["displayName"], f"{side}_team_abbr":team["abbreviation"],
                        f"{side}_score":int(c["score"]) if state in {"completed","in_progress"} and c.get("score") not in {None,""} else None})
        if state == "completed" and (row["home_score"] is None or row["away_score"] is None):
            raise ValueError("Completed game requires both final scores")
        rows.append(row)
    return rows

def apply_snapshot(snapshot, engine):
    from decimal import Decimal
    from sqlalchemy import text, select, insert
    from sqlalchemy.orm import Session
    from app.database.match_ingestion import upsert_match, resolve_match_references
    from app.database.betting_tables import markets, outcomes
    from app.services.virtual_betting import settle_match
    if engine.url.host not in {"localhost","127.0.0.1","::1"}: raise ValueError("Local database required")
    result=[]
    # Serialize this refresh with other instances of itself.
    with engine.connect() as conn:
        conn.execute(text("SELECT pg_advisory_lock(491055)")); conn.commit()
        try:
            for row in snapshot["matches"]:
                with conn.begin():
                    league=conn.execute(text("SELECT id,sport_id FROM leagues WHERE abbreviation=:league"),row).mappings().one()
                    conn.execute(text("INSERT INTO data_sources(name,source_type) VALUES (:source,'api') ON CONFLICT(name) DO NOTHING"), {"source":row["source"]})
                    source_id=conn.execute(text("SELECT id FROM data_sources WHERE name=:source"), {"source":row["source"]}).scalar_one()
                    for side in ("home","away"):
                        external=row[f"{side}_team_id"]
                        mapped=conn.execute(text("SELECT entity_id FROM external_mappings WHERE data_source_id=:source AND entity_type='team' AND external_id=:external"),{"source":source_id,"external":external}).scalar_one_or_none()
                        if mapped is None:
                            found=conn.execute(text("SELECT id FROM teams WHERE sport_id=:sport AND (name=:name OR abbreviation=:abbr)"),{"sport":league["sport_id"],"name":row[f"{side}_team_name"],"abbr":row[f"{side}_team_abbr"]}).scalars().all()
                            if len(found)>1: raise ValueError("Ambiguous team; resolve mapping before refresh")
                            team_id=found[0] if found else conn.execute(text("INSERT INTO teams(sport_id,name,abbreviation,active) VALUES (:sport,:name,:abbr,true) RETURNING id"),{"sport":league["sport_id"],"name":row[f"{side}_team_name"],"abbr":row[f"{side}_team_abbr"]}).scalar_one()
                            conn.execute(text("INSERT INTO external_mappings(data_source_id,entity_type,entity_id,external_id) VALUES (:source,'team',:team,:external)"),{"source":source_id,"team":team_id,"external":external})
                    # ESPN EPL season year is the starting calendar year.
                    year=row["season"]; label=f"{year}-{str(year+1)[-2:]}" if row["league"]=="EPL" else str(year)
                    seasons=conn.execute(text("SELECT id FROM seasons WHERE league_id=:league AND name=:name"),{"league":league["id"],"name":label}).scalars().all()
                    if len(seasons)>1: raise ValueError("Ambiguous season")
                    if not seasons: conn.execute(text("INSERT INTO seasons(league_id,name) VALUES (:league,:name)"),{"league":league["id"],"name":label})
                    previous=conn.execute(text("""SELECT m.status,m.home_score,m.away_score FROM matches m JOIN external_mappings e ON e.entity_id=m.id
                        WHERE e.data_source_id=:source AND e.entity_type='match' AND e.external_id=:external FOR UPDATE OF m"""),{"source":source_id,"external":row["game_id"]}).mappings().first()
                    if previous and previous["status"] in {"final","cancelled"}:
                        expected="final" if row["status"]=="completed" else row["status"]
                        if (previous["status"],previous["home_score"],previous["away_score"])!=(expected,row["home_score"],row["away_score"]):
                            raise ValueError("Completed result changed; review payout correction manually")
                    refs=resolve_match_references(conn,row,require_season=True)
                    mapping=conn.execute(text("SELECT entity_id FROM external_mappings WHERE data_source_id=:source AND entity_type='match' AND external_id=:external"),{"source":source_id,"external":row["game_id"]}).scalar_one_or_none()
                    if mapping is None:
                        candidates=conn.execute(text("""SELECT id,start_time,status,home_score,away_score FROM matches WHERE league_id=:league_id
                            AND home_team_id=:home_team_id AND away_team_id=:away_team_id
                            AND start_time >= CAST(:kickoff AS timestamptz)-interval '12 hours'
                            AND start_time <= CAST(:kickoff AS timestamptz)+interval '12 hours' FOR UPDATE"""),{**refs,"kickoff":row["kickoff_utc"]}).mappings().all()
                        exact=[m for m in candidates if m["start_time"]==datetime.fromisoformat(row["kickoff_utc"])]
                        if row["league"] == "MLB": candidates=exact
                        elif len(exact)==1: candidates=exact
                        if len(candidates)>1: raise ValueError("Ambiguous duplicate match; resolve mapping manually")
                        if candidates:
                            candidate=candidates[0]
                            if candidate["status"]=="final" and (candidate["home_score"],candidate["away_score"])!=(row["home_score"],row["away_score"]):
                                raise ValueError(f"Conflicting provider final scores: {row['league']} {row['game_id']} vs existing match {candidate['id']} ({candidate['home_score']}-{candidate['away_score']} vs {row['home_score']}-{row['away_score']})")
                            conn.execute(text("INSERT INTO external_mappings(data_source_id,entity_type,entity_id,external_id) VALUES (:source,'match',:id,:external)"),{"source":source_id,"id":candidate["id"],"external":row["game_id"]})
                            # Preserve the established precise kickoff across provider sources.
                            row={**row,"kickoff_utc":candidate["start_time"].isoformat()}
                    match_id=upsert_match(conn,row,references=refs)
                    for team_id in (refs["home_team_id"],refs["away_team_id"]):
                        conn.execute(text("INSERT INTO season_teams(season_id,team_id) VALUES (:season,:team) ON CONFLICT DO NOTHING"),{"season":refs["season_id"],"team":team_id})
                    # Never alter existing prices or re-open closed markets.
                    market=conn.execute(select(markets).where(markets.c.match_id==match_id)).mappings().first()
                    if market is None and row["status"]=="scheduled" and datetime.fromisoformat(row["kickoff_utc"])>datetime.now(timezone.utc):
                        mid=conn.execute(insert(markets).values(match_id=match_id,is_open=True).returning(markets.c.id)).scalar_one()
                        for selection in ["home","away"]+(["draw"] if row["league"]=="EPL" else []):
                            conn.execute(insert(outcomes).values(market_id=mid,selection=selection,decimal_odds=Decimal("2.5000")))
                # Settle only from provider final scores; repeat settlements are idempotent.
                if row["status"] in {"completed","cancelled"}:
                    with Session(engine) as db:
                        settle_match(db,match_id,row["home_score"],row["away_score"],row["status"]=="cancelled")
                result.append({"provider_id":row["game_id"],"match_id":match_id})
        finally:
            conn.rollback(); conn.execute(text("SELECT pg_advisory_unlock(491055)")); conn.commit()
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=Path("../build/real-fixtures.json"))
    parser.add_argument("--days-back",type=int,default=90)
    parser.add_argument("--days-ahead",type=int,default=14)
    parser.add_argument("--apply",action="store_true",help="Write reviewed fixtures, reference mappings and demo markets to configured localhost PostgreSQL")
    args=parser.parse_args()
    if not 0<=args.days_back<=730 or not 0<=args.days_ahead<=60: parser.error("Invalid date window")
    today=datetime.now(timezone.utc).date(); snapshot={"retrieved_at":datetime.now(timezone.utc).isoformat(),"source":"ESPN", "odds_source":"synthetic_demo", "matches":[],"sources":[]}
    for league,(feed,_) in FEEDS.items():
        start=today-timedelta(days=args.days_back); end=today+timedelta(days=args.days_ahead)
        while start<=end:
            stop=start
            url=f"https://site.api.espn.com/apis/site/v2/sports/{feed}/scoreboard?dates={start:%Y%m%d}&limit=1000"
            with urlopen(url,timeout=30) as response: raw=response.read()
            payload=json.loads(raw)
            if len(payload.get("events",[]))>=1000: raise ValueError("Feed may be truncated; use smaller windows")
            snapshot["sources"].append({"url":url,"sha256":hashlib.sha256(raw).hexdigest()})
            snapshot["matches"].extend(normalize(payload,league)); start=stop+timedelta(days=1)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(snapshot,indent=2)+"\n")
    print(f"Saved {len(snapshot['matches'])} real fixtures to {args.output}")
    if args.apply:
        from app.database.db import engine
        print(json.dumps(apply_snapshot(snapshot,engine),indent=2))

if __name__=="__main__": main()
