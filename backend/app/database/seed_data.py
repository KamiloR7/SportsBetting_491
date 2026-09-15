"""
Sprint 1 reference/domain seed data for the sports_betting database.

Populates: sports -> leagues -> teams (in that order, respecting foreign keys).

Safe to run more than once: sports are upserted via slug (unique constraint),
and leagues/teams are only inserted if a matching row does not already exist.

Run from the backend/ directory with the virtualenv active:
    python -m app.database.seed_data
"""

from sqlalchemy import text

from app.database.db import engine

SPORTS = [
    {"name": "Basketball", "slug": "basketball"},
    {"name": "American Football", "slug": "american-football"},
    {"name": "Baseball", "slug": "baseball"},
    {"name": "Hockey", "slug": "hockey"},
    {"name": "Soccer", "slug": "soccer"},
]

LEAGUES = [
    {"sport_slug": "basketball", "name": "National Basketball Association", "abbreviation": "NBA", "country": "USA"},
    {"sport_slug": "american-football", "name": "National Football League", "abbreviation": "NFL", "country": "USA"},
    {"sport_slug": "baseball", "name": "Major League Baseball", "abbreviation": "MLB", "country": "USA"},
    {"sport_slug": "hockey", "name": "National Hockey League", "abbreviation": "NHL", "country": "USA/Canada"},
    {"sport_slug": "soccer", "name": "English Premier League", "abbreviation": "EPL", "country": "England"},
]

TEAMS = [
    # NBA
    {"sport_slug": "basketball", "name": "Los Angeles Lakers", "abbreviation": "LAL", "city": "Los Angeles"},
    {"sport_slug": "basketball", "name": "Boston Celtics", "abbreviation": "BOS", "city": "Boston"},
    {"sport_slug": "basketball", "name": "Golden State Warriors", "abbreviation": "GSW", "city": "San Francisco"},
    {"sport_slug": "basketball", "name": "Miami Heat", "abbreviation": "MIA", "city": "Miami"},
    {"sport_slug": "basketball", "name": "Chicago Bulls", "abbreviation": "CHI", "city": "Chicago"},
    {"sport_slug": "basketball", "name": "Denver Nuggets", "abbreviation": "DEN", "city": "Denver"},
    # NFL
    {"sport_slug": "american-football", "name": "Kansas City Chiefs", "abbreviation": "KC", "city": "Kansas City"},
    {"sport_slug": "american-football", "name": "Philadelphia Eagles", "abbreviation": "PHI", "city": "Philadelphia"},
    {"sport_slug": "american-football", "name": "Dallas Cowboys", "abbreviation": "DAL", "city": "Dallas"},
    {"sport_slug": "american-football", "name": "San Francisco 49ers", "abbreviation": "SF", "city": "San Francisco"},
    {"sport_slug": "american-football", "name": "Buffalo Bills", "abbreviation": "BUF", "city": "Buffalo"},
    {"sport_slug": "american-football", "name": "Green Bay Packers", "abbreviation": "GB", "city": "Green Bay"},
    # MLB
    {"sport_slug": "baseball", "name": "New York Yankees", "abbreviation": "NYY", "city": "New York"},
    {"sport_slug": "baseball", "name": "Los Angeles Dodgers", "abbreviation": "LAD", "city": "Los Angeles"},
    {"sport_slug": "baseball", "name": "Boston Red Sox", "abbreviation": "BOS", "city": "Boston"},
    {"sport_slug": "baseball", "name": "Chicago Cubs", "abbreviation": "CHC", "city": "Chicago"},
    {"sport_slug": "baseball", "name": "Houston Astros", "abbreviation": "HOU", "city": "Houston"},
    {"sport_slug": "baseball", "name": "Atlanta Braves", "abbreviation": "ATL", "city": "Atlanta"},
    # NHL
    {"sport_slug": "hockey", "name": "Toronto Maple Leafs", "abbreviation": "TOR", "city": "Toronto"},
    {"sport_slug": "hockey", "name": "Montreal Canadiens", "abbreviation": "MTL", "city": "Montreal"},
    {"sport_slug": "hockey", "name": "Boston Bruins", "abbreviation": "BOS", "city": "Boston"},
    {"sport_slug": "hockey", "name": "New York Rangers", "abbreviation": "NYR", "city": "New York"},
    {"sport_slug": "hockey", "name": "Colorado Avalanche", "abbreviation": "COL", "city": "Denver"},
    {"sport_slug": "hockey", "name": "Edmonton Oilers", "abbreviation": "EDM", "city": "Edmonton"},
    # EPL
    {"sport_slug": "soccer", "name": "Manchester United", "abbreviation": "MUN", "city": "Manchester"},
    {"sport_slug": "soccer", "name": "Manchester City", "abbreviation": "MCI", "city": "Manchester"},
    {"sport_slug": "soccer", "name": "Liverpool", "abbreviation": "LIV", "city": "Liverpool"},
    {"sport_slug": "soccer", "name": "Arsenal", "abbreviation": "ARS", "city": "London"},
    {"sport_slug": "soccer", "name": "Chelsea", "abbreviation": "CHE", "city": "London"},
    {"sport_slug": "soccer", "name": "Tottenham Hotspur", "abbreviation": "TOT", "city": "London"},
]


def seed_sports(conn):
    """Insert sports, or do nothing if the slug already exists. Returns {slug: id}."""
    sport_ids = {}
    for sport in SPORTS:
        conn.execute(
            text(
                """
                INSERT INTO sports (name, slug)
                VALUES (:name, :slug)
                ON CONFLICT (slug) DO NOTHING
                """
            ),
            sport,
        )
        row = conn.execute(
            text("SELECT id FROM sports WHERE slug = :slug"),
            {"slug": sport["slug"]},
        ).first()
        sport_ids[sport["slug"]] = row.id
    return sport_ids


def seed_leagues(conn, sport_ids):
    """Insert leagues that don't already exist (matched by name)."""
    for league in LEAGUES:
        sport_id = sport_ids[league["sport_slug"]]
        existing = conn.execute(
            text("SELECT id FROM leagues WHERE name = :name"),
            {"name": league["name"]},
        ).first()
        if existing:
            continue
        conn.execute(
            text(
                """
                INSERT INTO leagues (sport_id, name, abbreviation, country)
                VALUES (:sport_id, :name, :abbreviation, :country)
                """
            ),
            {
                "sport_id": sport_id,
                "name": league["name"],
                "abbreviation": league["abbreviation"],
                "country": league["country"],
            },
        )


def seed_teams(conn, sport_ids):
    """Insert teams that don't already exist (matched by sport_id + name)."""
    for team in TEAMS:
        sport_id = sport_ids[team["sport_slug"]]
        existing = conn.execute(
            text("SELECT id FROM teams WHERE sport_id = :sport_id AND name = :name"),
            {"sport_id": sport_id, "name": team["name"]},
        ).first()
        if existing:
            continue
        conn.execute(
            text(
                """
                INSERT INTO teams (sport_id, name, abbreviation, city)
                VALUES (:sport_id, :name, :abbreviation, :city)
                """
            ),
            {
                "sport_id": sport_id,
                "name": team["name"],
                "abbreviation": team["abbreviation"],
                "city": team["city"],
            },
        )


def run_seed():
    with engine.begin() as conn:
        sport_ids = seed_sports(conn)
        seed_leagues(conn, sport_ids)
        seed_teams(conn, sport_ids)


if __name__ == "__main__":
    run_seed()
    print("Seed data applied (sports, leagues, teams).")
