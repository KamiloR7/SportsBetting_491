"""Public provider standings, separate from incomplete local match history."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import math
import logging
from pathlib import Path
from threading import Lock
from urllib.request import urlopen
from app.services.team_branding import team_brand, clean_logo

logger=logging.getLogger(__name__)

EXPECTED={"NFL":32,"MLB":30,"EPL":20}
ESPN_FEEDS={"NFL":"football/nfl","EPL":"soccer/eng.1"}
# IDs/names verified against MLB's official /api/v1/divisions?sportId=1.
MLB_DIVISIONS={201:("American League","AL East"),202:("American League","AL Central"),200:("American League","AL West"),204:("National League","NL East"),205:("National League","NL Central"),203:("National League","NL West")}

class StandingsUnavailable(RuntimeError):pass


def _number(value,default=-1):
    try:
        result=float(value)
        return result if math.isfinite(result) else default
    except (TypeError,ValueError):return default


def _display(value):
    if value is None:return "—"
    if isinstance(value,float) and value.is_integer():return str(int(value))
    return str(value)


def _signed(value):
    number=_number(value,None)
    return ("+" if number and number>0 else "")+_display(value)


def _team(league,raw):
    name=raw.get("displayName") or raw.get("name")
    if not name or raw.get("id") is None:raise StandingsUnavailable("Missing team identity")
    brand=team_brand(league,name)
    logo=brand.get("logo_url") or next((clean_logo(item.get("href")) for item in raw.get("logos",[]) if clean_logo(item.get("href"))),None)
    return {"id":str(raw["id"]),"name":brand.get("name",name),"abbreviation":raw.get("abbreviation"),
            "logo_url":logo,"primary_color":brand.get("primary_color"),"secondary_color":brand.get("secondary_color")}


def _finish(league,season,label,source,url,groups,rows,now):
    if len(rows)!=EXPECTED[league] or len({r["team"]["id"] for r in rows})!=EXPECTED[league]:
        raise StandingsUnavailable("Incomplete or duplicated provider standings")
    overall=sorted(rows,key=lambda row:-row["sort_pct"])
    if league=="MLB" and all(row.get("overall_rank",0)>0 for row in rows):overall=sorted(rows,key=lambda row:row["overall_rank"])
    overall=[{**row,"overall_position":index+1} for index,row in enumerate(overall)]
    return {"league":league,"season":str(season),"season_label":str(label),"season_type":"League table" if league=="EPL" else "Regular season",
            "source":source,"source_url":url,"retrieved_at":now.isoformat(),"cache_ttl_seconds":300,
            "groups":groups,"overall":overall,"team_count":len(rows),"stale":False,
            "views":["table"] if league=="EPL" else ["conference","overall"] if league=="NFL" else ["division","league","overall"],
            "default_view":"table" if league=="EPL" else "conference" if league=="NFL" else "division"}


def normalize_espn(league,payload,now=None):
    now=now or datetime.now(timezone.utc);groups=[];rows=[];seasons=set();labels=set()
    for child in payload.get("children",[]):
        standing=child.get("standings",{});entries=standing.get("entries",[])
        if not entries:continue
        season=standing.get("season")
        if isinstance(season,dict):season=season.get("year")
        if not season:raise StandingsUnavailable("Missing standings season")
        seasons.add(str(season));labels.add(standing.get("seasonDisplayName") or str(season))
        grouped=[]
        for index,entry in enumerate(entries):
            stats={item.get("name"):item for item in entry.get("stats",[])}
            required=["wins","losses","ties"]
            if any(key not in stats or _number(stats[key].get("value"))<0 for key in required):raise StandingsUnavailable("Missing standings record")
            if league=="NFL" and not 0<=_number(stats.get("winPercent",{}).get("value"))<=1:raise StandingsUnavailable("Missing NFL win percentage")
            if league=="EPL" and _number(stats.get("points",{}).get("value"),None) is None:raise StandingsUnavailable("Missing EPL points")
            def value(name):
                item=stats.get(name,{})
                return _display(item.get("displayValue") if item.get("displayValue") is not None else item.get("value"))
            values={"wins":value("wins"),"losses":value("losses"),"ties":value("ties"),"pct":value("winPercent"),
                    "played":value("gamesPlayed"),"for":value("pointsFor"),"against":value("pointsAgainst"),
                    "difference":value("pointDifferential"),"streak":value("streak"),"points":value("points")}
            rank=int(_number(stats.get("rank",{}).get("value"),index+1))
            row={"team":_team(league,entry["team"]),"stats":values,"sort_pct":_number(stats.get("winPercent",{}).get("value")),
                 "provider_rank":rank if rank>0 else index+1,"group_label":child.get("abbreviation") or child.get("name","")}
            grouped.append(row);rows.append(row)
        if league=="EPL":grouped.sort(key=lambda row:row["provider_rank"])
        groups.append({"id":str(child.get("id",len(groups))),"name":child.get("name",league),"short_name":child.get("abbreviation"),
                       "kind":"table" if league=="EPL" else "conference","rows":grouped})
    if len(seasons)!=1:raise StandingsUnavailable("Mixed or missing provider seasons")
    label=sorted(labels)[0]
    return _finish(league,next(iter(seasons)),label,"ESPN",f"https://site.api.espn.com/apis/v2/sports/{ESPN_FEEDS[league]}/standings",groups,rows,now)


def normalize_mlb(payload,season,now=None):
    now=now or datetime.now(timezone.utc);rows=[];division_groups={};league_groups={}
    for record in payload.get("records",[]):
        division_id=record.get("division",{}).get("id")
        if division_id not in MLB_DIVISIONS:raise StandingsUnavailable("Unknown MLB division")
        league_name,division_name=MLB_DIVISIONS[division_id];grouped=[]
        for entry in record.get("teamRecords",[]):
            if str(entry.get("season"))!=str(season):raise StandingsUnavailable("Mixed MLB seasons")
            wins=entry.get("wins");losses=entry.get("losses")
            if _number(wins)<0 or _number(losses)<0:raise StandingsUnavailable("Missing MLB record")
            pct=entry.get("winningPercentage",entry.get("leagueRecord",{}).get("pct"))
            if not 0<=_number(pct)<=1:raise StandingsUnavailable("Missing MLB win percentage")
            if any(_number(entry.get(key),0)<1 for key in ("divisionRank","leagueRank","sportRank")):raise StandingsUnavailable("Missing MLB rank")
            values={"wins":_display(wins),"losses":_display(losses),"pct":_display(pct),"for":_display(entry.get("runsScored")),
                    "against":_display(entry.get("runsAllowed")),"difference":_signed(entry.get("runDifferential")),
                    "streak":entry.get("streak",{}).get("streakCode","—"),"gb_division":_display(entry.get("divisionGamesBack")),
                    "gb_league":_display(entry.get("leagueGamesBack")),"gb_overall":_display(entry.get("sportGamesBack"))}
            row={"team":_team("MLB",entry["team"]),"stats":values,"sort_pct":_number(pct),
                 "provider_rank":int(_number(entry.get("divisionRank"),0)),"league_rank":int(_number(entry.get("leagueRank"),0)),
                 "overall_rank":int(_number(entry.get("sportRank"),0)),"group_label":division_name}
            grouped.append(row);rows.append(row);league_groups.setdefault(league_name,[]).append(row)
        grouped.sort(key=lambda row:(row["provider_rank"] or 999,-row["sort_pct"]))
        division_groups[division_id]={"id":str(division_id),"name":division_name,"short_name":division_name,"kind":"division","rows":grouped}
    groups=[division_groups[key] for key in MLB_DIVISIONS if key in division_groups]
    for name,items in league_groups.items():
        groups.append({"id":name,"name":name,"kind":"league","rows":sorted(items,key=lambda row:(row["league_rank"] or 999,-row["sort_pct"]))})
    return _finish("MLB",season,season,"MLB Stats API",f"https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season={season}&standingsTypes=regularSeason",groups,rows,now)


def fetch_standings(league,opener=urlopen,now=None):
    now=now or datetime.now(timezone.utc)
    def read(url):
        with opener(url,timeout=12) as response:return json.load(response)
    if league in ESPN_FEEDS:
        return normalize_espn(league,read(f"https://site.api.espn.com/apis/v2/sports/{ESPN_FEEDS[league]}/standings"),now)
    if league=="MLB":
        for season in (now.year,now.year-1):
            data=read(f"https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season={season}&standingsTypes=regularSeason")
            entries=[entry for record in data.get("records",[]) for entry in record.get("teamRecords",[])]
            if entries and any(_number(entry.get("wins"),0)+_number(entry.get("losses"),0)>0 for entry in entries):
                return normalize_mlb(data,season,now)
    raise StandingsUnavailable("No played regular season available")


class StandingsCache:
    def __init__(self,directory=None,fetcher=fetch_standings,clock=None,ttl=300):
        self.directory=Path(directory) if directory else Path(__file__).resolve().parents[3]/"build/standings"
        self.fetcher=fetcher;self.clock=clock or (lambda:datetime.now(timezone.utc));self.ttl=ttl
        self.data={};self.attempts={};self.locks={league:Lock() for league in EXPECTED}

    def get(self,league):
        if league not in EXPECTED:raise StandingsUnavailable("Unsupported league")
        with self.locks[league]:
            now=self.clock();path=self.directory/f"{league.lower()}.json"
            if league not in self.data:
                try:
                    saved=json.loads(path.read_text(encoding="utf-8"))
                    if saved["league"]==league and saved["team_count"]==EXPECTED[league] and datetime.fromisoformat(saved["retrieved_at"]).tzinfo:
                        self.data[league]=saved
                except (OSError,ValueError,KeyError,TypeError):pass
            current=self.data.get(league)
            if current:
                age=(now-datetime.fromisoformat(current["retrieved_at"])).total_seconds()
                if 0<=age<self.ttl:return deepcopy(current)
            last_attempt=self.attempts.get(league)
            if last_attempt is None or (now-last_attempt).total_seconds()>=60:
                self.attempts[league]=now
                try:
                    fresh=self.fetcher(league)
                    self.data[league]=fresh
                    try:
                        path.parent.mkdir(parents=True,exist_ok=True)
                        temp=path.with_suffix(".next.json");temp.write_text(json.dumps(fresh),encoding="utf-8");temp.replace(path)
                    except OSError:pass
                    return deepcopy(fresh)
                except Exception as exc:logger.warning("Standings refresh failed for %s (%s)",league,type(exc).__name__)
            if current:
                result=deepcopy(current);result.update(stale=True,warning="Provider update unavailable. Showing last saved standings.")
                return result
            raise StandingsUnavailable("Standings are temporarily unavailable. Please try again shortly.")


standings_cache=StandingsCache()
