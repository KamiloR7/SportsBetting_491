"""Explicit synthetic scheduled fixtures and database-backed demo odds."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import text, insert
from app.database.betting_tables import markets, outcomes


def create_demo_fixtures(db):
    created=[]
    for abbreviation in ['EPL','NFL','MLB']:
        league=db.execute(text('SELECT id,sport_id FROM leagues WHERE abbreviation=:name'),{'name':abbreviation}).mappings().one()
        teams=db.execute(text('SELECT id FROM teams WHERE sport_id=:id ORDER BY id LIMIT 2'),{'id':league['sport_id']}).scalars().all()
        if len(teams)!=2: raise ValueError(f'{abbreviation} requires two reference teams.')
        match_id=db.execute(text("""INSERT INTO matches (league_id,home_team_id,away_team_id,start_time,status,neutral_site)
            VALUES (:league,:home,:away,:start,'scheduled',false) RETURNING id"""),
            {'league':league['id'],'home':teams[0],'away':teams[1],'start':datetime.now(timezone.utc)+timedelta(days=7)}).scalar_one()
        market_id=db.execute(insert(markets).values(match_id=match_id,is_open=True).returning(markets.c.id)).scalar_one()
        for selection in ['home','away']+(['draw'] if abbreviation=='EPL' else []):
            db.execute(insert(outcomes).values(market_id=market_id,selection=selection,decimal_odds=Decimal('2.5000')))
        created.append({'league':abbreviation,'match_id':match_id,'odds_source':'synthetic_demo'})
    db.commit()
    return created
