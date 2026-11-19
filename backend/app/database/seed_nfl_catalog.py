"""Complete the fresh-install NFL reference catalogue; no fixtures or odds."""
import json
from pathlib import Path
from urllib.parse import urlparse
from sqlalchemy import text


def seed_nfl_catalog(engine):
    catalog = json.loads((Path(__file__).resolve().parents[1] / "data/team_branding.json").read_text(encoding="utf-8"))
    teams = [(Path(urlparse(t["logo_url"]).path).stem.upper(), t["name"]) for t in catalog["teams"] if t["league"] == "NFL"]
    if len(teams) != 32 or len({abbr for abbr, _ in teams}) != 32:
        raise ValueError("Expected 32 unique NFL reference profiles")
    with engine.begin() as conn:
        sport = conn.execute(text("SELECT id FROM sports WHERE slug='american-football'")).scalar_one()
        for abbreviation, name in teams:
            existing = conn.execute(text("SELECT name FROM teams WHERE sport_id=:sport AND abbreviation=:abbr"), {"sport": sport, "abbr": abbreviation}).scalars().all()
            if existing and existing != [name]:
                raise ValueError("Conflicting NFL team mapping; review existing reference data")
            if not existing:
                conn.execute(text("INSERT INTO teams(sport_id,name,abbreviation,active) VALUES (:sport,:name,:abbr,true)"), {"sport": sport, "name": name, "abbr": abbreviation})


if __name__ == "__main__":
    from app.database.db import engine
    if engine.url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise SystemExit("Local database required")
    seed_nfl_catalog(engine)
    print("All 32 NFL reference teams are available. No matches or odds were created.")
