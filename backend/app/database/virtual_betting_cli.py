"""Explicit local operator actions. Never registered as HTTP endpoints."""
import argparse
from sqlalchemy.orm import Session
from app.database.db import engine
from app.database.setup_virtual_betting import initialize_virtual_betting
from app.services.virtual_betting import settle_match
from app.database.virtual_demo_fixtures import create_demo_fixtures


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command', required=True)
    sub.add_parser('setup', help='Add auth and virtual betting tables; obtain database owner approval first')
    sub.add_parser('seed-demo', help='Insert three synthetic matches and demo odds; each run creates new fixtures')
    settle=sub.add_parser('settle')
    settle.add_argument('match_id', type=int)
    settle.add_argument('--home-score', type=int)
    settle.add_argument('--away-score', type=int)
    settle.add_argument('--void', action='store_true')
    args=parser.parse_args()
    if engine.url.host not in {'localhost','127.0.0.1','::1'}:
        parser.error('Only a local database is permitted.')
    if args.command=='setup':
        try:
            initialize_virtual_betting(engine)
        except ValueError as exc:
            parser.error(str(exc))
        print('Additive virtual betting setup complete.')
    elif args.command == 'seed-demo':
        with Session(engine) as db:
            print(create_demo_fixtures(db))
    else:
        with Session(engine) as db:
            print(settle_match(db,args.match_id,args.home_score,args.away_score,args.void))

if __name__=='__main__': main()
