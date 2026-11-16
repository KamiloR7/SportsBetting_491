"""Verified provider presentation metadata; never guessed team identities/colors."""
import json
import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

CATALOG_PATH=Path(__file__).resolve().parents[1]/"data/team_branding.json"
LEAGUES={"nfl":"NFL","national football league":"NFL","mlb":"MLB","major league baseball":"MLB","epl":"EPL","english premier league":"EPL","premier league":"EPL"}


def clean_color(value):
    return "#"+value.lower() if isinstance(value,str) and re.fullmatch(r"[0-9a-fA-F]{6}",value) else None


def clean_logo(value):
    if not isinstance(value,str):return None
    parsed=urlsplit(value)
    return value if parsed.scheme=="https" and parsed.netloc=="a.espncdn.com" and parsed.path.startswith("/i/teamlogos/") else None


def normalize_team(league,team):
    aliases=sorted({team.get(key,"").strip() for key in ("displayName","shortDisplayName","name") if isinstance(team.get(key),str) and team[key].strip()})
    # The historical Oakland name is the same Athletics franchise. Images and
    # colors describe the current provider profile, not a period-specific kit.
    if league=="MLB" and team.get("displayName")=="Athletics":aliases.append("Oakland Athletics")
    logos=team.get("logos",[])
    logo=next((clean_logo(item.get("href")) for item in logos if "default" in item.get("rel",[]) and clean_logo(item.get("href"))),None)
    if logo is None:logo=next((clean_logo(item.get("href")) for item in logos if clean_logo(item.get("href"))),None)
    return {"league":league,"provider_id":str(team["id"]),"name":team["displayName"],"aliases":aliases,
            "primary_color":clean_color(team.get("color")),"secondary_color":clean_color(team.get("alternateColor")),"logo_url":logo}


def build_index(teams):
    result={}
    for team in teams:
        for name in team["aliases"]:
            key=(team["league"],name.casefold().strip())
            if key in result and (result[key] is None or result[key]["provider_id"]!=team["provider_id"]):result[key]=None
            else:result[key]=team
    return result


@lru_cache(maxsize=1)
def catalog_index():
    try:return build_index(json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["teams"])
    except (OSError,ValueError,KeyError):return {}


def team_brand(league,name):
    code=LEAGUES.get((league or "").casefold().strip())
    return catalog_index().get((code,(name or "").casefold().strip())) or {}


def match_brand_fields(league,home,away):
    result={}
    for side,name in (("home",home),("away",away)):
        brand=team_brand(league,name)
        for field in ("primary_color","secondary_color","logo_url"):result[f"{side}_{field}"]=brand.get(field)
    return result
