"""Explicit refresh of public team colors and logo URLs; no database changes."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen
from app.services.team_branding import CATALOG_PATH, normalize_team

DIRECTORIES=[("NFL","football/nfl"),("MLB","baseball/mlb"),("EPL","soccer/eng.1"),("EPL","soccer/eng.2"),("EPL","soccer/eng.3")]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=CATALOG_PATH)
    args=parser.parse_args();records={};sources=[]
    for league,feed in DIRECTORIES:
        url=f"https://site.api.espn.com/apis/site/v2/sports/{feed}/teams?limit=1000"
        with urlopen(url,timeout=20) as response:payload=json.load(response)
        teams=[item["team"] for sport in payload.get("sports",[]) for group in sport.get("leagues",[]) for item in group.get("teams",[])]
        if not teams:raise ValueError("Empty provider team directory; existing catalog retained")
        sources.append(url)
        for team in teams:records.setdefault((league,str(team["id"])),normalize_team(league,team))
    output={"source":"ESPN team directories","retrieved_at":datetime.now(timezone.utc).isoformat(),"source_urls":sources,
            "branding_period":"Current provider profile; historical names do not imply period-specific logos.",
            "teams":sorted(records.values(),key=lambda item:(item["league"],item["name"]))}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    temporary=args.output.with_suffix(".next.json");temporary.write_text(json.dumps(output,indent=2)+"\n",encoding="utf-8");temporary.replace(args.output)
    print(f"Saved {len(records)} verified team profiles to {args.output}. Restart the backend to reload.")

if __name__=="__main__":main()
