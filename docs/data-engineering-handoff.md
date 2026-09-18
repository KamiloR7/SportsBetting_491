# Sprint 1 data engineering handoff

Run all commands from the repository root unless stated otherwise. Use Python 3.10 or newer for the combined collector suite.

## Install and test

```sh
python -m pip install -e . pytest
python -m pytest -v
```

The offline data-engineering suite contains 34 tests: NBA 4, NFL 8, UEFA 11, and normalizer 11. The tests use fixtures/injected loaders and do not establish live provider availability. The September 17 integration run passed all 34 tests.

## Collect data

NBA uses ESPN and exports JSON, including metadata:

```sh
python -m sportsbetting.collectors.nba --start-date 2026-09-01 --end-date 2026-09-17 --output-dir data/raw/nba
```

NFL requires `python -m pip install nflreadpy` for live collection:

```sh
python nfl_collector.py --season 2026 --output-dir data/development
```

UEFA Champions League requires the FOOTBALL_DATA_API_TOKEN environment variable, configured locally:

```sh
python uefa_collector.py --season 2026 --output-dir data/development
```

The UEFA season is the competition's starting year. Never commit an API token.

## Normalize NFL and UEFA CSV files

```sh
cd backend
python -m src.normalizers.multi_sport_normalizer \
  --teams ../data/development/nfl_teams.csv ../data/development/uefa_cl_teams.csv \
  --matches ../data/development/nfl_games_2026.csv ../data/development/uefa_cl_games_2026.csv \
  --output-dir ../data/normalized
```

Outputs are teams.csv and matches.csv. The normalizer uses (sport, league, ID) identities, validates participant references, rejects conflicting duplicates, converts numeric fields, and derives missing final winners. NFL maps to FOOTBALL, UEFA/EPL to SOCCER, and MLB to BASEBALL. Future sport aliases are not evidence of an implemented collector. NBA JSON requires a separate adapter before this CSV pipeline can consume it.

## Source and test locations

- NBA: src/sportsbetting/collectors/nba.py and tests/test_nba_collector.py
- NFL: nfl_collector.py and test_nfl_collector.py
- UEFA: uefa_collector.py and test_uefa_collector.py
- Normalizer: backend/src/normalizers/multi_sport_normalizer.py and backend/tests/test_multi_sport_normalizer.py
- Research: m1-sports-data-sources-research.md

The NBA files were restored from the existing local review commit, which held the implementation previously submitted as a patch. Existing NFL/UEFA tests now import the actual root-level collector modules. Pytest configuration adds the source roots and collects all four suites.

## Remaining reliability work

SCRUM-10 remains in progress. Follow-ups include explicit HTTP authorization/rate-limit/timeout tests, CSV header validation, UEFA home-venue fallback where appropriate, stronger validation of explicitly supplied winners, and consistent NFL season validation. NFL final status currently depends on score availability. No live API retrieval or production ingestion is established by the offline tests.
