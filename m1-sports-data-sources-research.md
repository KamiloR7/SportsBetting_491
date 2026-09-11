# M1 Research: NBA, NFL, and UEFA Data Sources/APIs

Date researched: 2026-09-11

## Scope

This research compares practical data/API options for NBA, NFL, and UEFA competitions, with emphasis on:

- Schedules, teams, players, rosters, standings
- Live scores and game state
- Box scores, player/team stats, play-by-play or event data
- Odds/fantasy/betting-related feeds where available
- Licensing, reliability, and production suitability

## Executive Recommendation

Use different source classes depending on the product requirement:

| Scenario | Recommended path |
| --- | --- |
| Commercial product requiring official/rights-clean data | NBA: Sportradar NBA. NFL: Genius Sports for official NFL data/Next Gen Stats/betting feed. UEFA: Sportradar Soccer/Soccer Extended or Stats Perform/Opta. |
| Paid MVP with broad coverage and lower integration friction | SportsDataIO for NBA/NFL/Soccer or API-Football/BALLDONTLIE for UEFA and sports coverage. |
| Analytics prototype or internal research | NBA: nba_api/BALLDONTLIE. NFL: nflverse/nfldata.org. UEFA: football-data.org, API-Football, StatsBomb open data, openfootball. |
| Public/free only | Feasible for prototypes, but not recommended for live commercial apps because of licensing, freshness, uptime, and endpoint stability concerns. |

Avoid scraping NBA.com or UEFA.com for a public/commercial product. NBA.com statistics terms restrict commercial, fantasy, gambling, play-by-play, and regularly updated database use without permission. UEFA terms prohibit systematic collection/scraping of UEFA platform content and limit platform content to private non-commercial access.

## Source Shortlist

### 1. Sportradar

Best fit: production-grade NBA and UEFA/soccer data; possible NFL media-data use if its license fits the product.

- NBA API: official-source B2B REST API, current version v8, JSON/XML, API-key authentication, deep league-specific basketball feeds.
- NFL API: B2B REST API, current version v7, JSON/XML, API-key authentication, 30+ feeds, REST plus push feeds for real-time customers.
- Soccer API: B2B REST API, current version v4, 650+ competitions, 52 feeds, tiered coverage, Soccer Extended add-on for deeper stats.
- Strengths: strong documentation, trial flow, official/commercial posture, live and historical coverage, broad sport portfolio.
- Tradeoffs: B2B pricing/sales process; keys should stay server-side; coverage tiers must be validated for each competition.

Sources:

- https://developer.sportradar.com/basketball/docs/nba-ig-api-basics
- https://developer.sportradar.com/football/docs/nfl-ig-api-basics
- https://developer.sportradar.com/soccer/docs/soccer-ig-api-basics
- https://developer.sportradar.com/soccer/reference/soccer-overview
- https://developer.sportradar.com/getting-started/docs/get-started
- https://developer.sportradar.com/getting-started/docs/authentication

### 2. Genius Sports

Best fit: official NFL production feeds, especially official real-time play-by-play, Next Gen Stats, and betting data.

- NFL.com states Genius Sports remains the NFL's exclusive distributor of real-time official play-by-play statistics, Next Gen Stats data, and the official sports betting data feed through the 2027-28 season.
- Developer center includes REST and streaming APIs for matches, players, statistics, fixtures, and live data workflows.
- Strengths: official NFL data position; strongest choice if the app needs official NFL data, low latency, NGS, sportsbook-grade feeds.
- Tradeoffs: enterprise/B2B sales; likely higher cost and contract requirements.

Sources:

- https://www.nfl.com/news/nfl-extends-strategic-partnership-with-genius-sports
- https://www.geniussports.com/engage/official-sports-data-api/
- https://developer.geniussports.com/

### 3. SportsDataIO

Best fit: commercial-friendly NBA/NFL/Soccer integration with event, betting, fantasy, and news/image feeds.

- League APIs cover deep league-specific feeds for NBA and NFL.
- Global Sports API provides a newer, more consistent cross-sport model.
- Available feed families include competition, event, player, betting, fantasy, and news/images.
- Soccer workflow guide explicitly covers UEFA Champions League use cases, including competition/tournament standings, live game state, injuries for UEFA Champions League, odds, and DFS/salaries for Champions League group stage and beyond.
- Strengths: broad commercial product surface; self-serve trial/replay options plus sales/development keys; good for fantasy and betting use cases.
- Tradeoffs: production/live data requires paid/commercial access; trial data may be scrambled depending on access method.

Sources:

- https://sportsdata.io/developers
- https://sportsdata.io/developers/apis
- https://sportsdata.io/developers/available-data-feeds
- https://sportsdata.io/developers/api-documentation/nba
- https://sportsdata.io/developers/api-documentation/nfl
- https://sportsdata.io/developers/workflow-guide/soccer
- https://sportsdata.io/developers/api-documentation/global

### 4. Stats Perform / Opta

Best fit: premium UEFA/soccer data, rich historical/event data, analytics, betting, and media products.

- Offers APIs/data feeds for live match data, historical statistics, player/team analytics, predictions, odds, video, headshots, and editorial content.
- Opta data supports real-time stats, advanced metrics such as xG, and broad coverage across thousands of competitions.
- Delivery options include REST APIs, websockets, push/pull feeds, S3 buckets, JSON/XML, and API-key authentication.
- Strengths: top-tier football/soccer data depth; strong for media, sportsbook, and analytics products.
- Tradeoffs: sales-led access/pricing; public documentation is less self-serve than lower-cost APIs.

Sources:

- https://www.statsperform.com/stats-perform-faqs-apis-and-data-delivery/
- https://www.statsperform.com/insights/crafting-next-gen-sports-apps-and-media-experiences-with-stats-performs-opta-apis/
- https://www.statsperform.com/products/
- https://developers.statsperform.com/

### 5. BALLDONTLIE

Best fit: low-cost/self-serve sports API for MVPs, prototypes, and small products.

- NBA API includes teams, players, games, stats, standings, betting odds, player props, DFS slates, and real-time game/stat data.
- NFL API includes teams and other NFL sports data endpoints.
- Champions League API includes matches/standings/odds/futures per the documentation index; UCL odds endpoints are documented separately.
- Pricing docs show free and low-cost paid plans with rate limits ranging from small free-tier usage to higher paid limits.
- Strengths: straightforward API-key auth, self-serve, inexpensive compared with enterprise feeds.
- Tradeoffs: not official; data quality, terms, latency, and coverage should be validated before production reliance.

Sources:

- https://www.balldontlie.io/docs/
- https://docs.balldontlie.io/
- https://nfl.balldontlie.io/
- https://ucl.balldontlie.io/
- https://www.balldontlie.io/account/

### 6. football-data.org

Best fit: UEFA Champions League fixtures, schedules, standings, and lightweight soccer data.

- Free tier includes Champions League among 12 competitions, with delayed scores/schedules and league tables.
- Paid tiers add live scores, deeper data, more competitions, history, lineup/substitution/scorer/card/squad data, and higher call limits.
- Uses `X-Auth-Token` authentication.
- Champions League code is `CL`; lookup table also includes Europa League, Conference League, UEFA European Championship, UEFA Super Cup, and UEFA qualification.
- Strengths: simple, affordable, useful for schedule/standings-heavy apps.
- Tradeoffs: less detailed than Sportradar/Opta/SportsDataIO; rate limits and feature depth vary by tier.

Sources:

- https://www.football-data.org/documentation/api
- https://www.football-data.org/documentation/quickstart
- https://www.football-data.org/coverage
- https://www.football-data.org/pricing
- https://docs.football-data.org/general/v4/lookup_tables.html

### 7. API-Football

Best fit: low-cost UEFA/soccer coverage with broad endpoint coverage.

- Free plan includes 100 requests/day.
- Paid plans include larger daily quotas and access to countries, seasons, leagues, standings, teams, livescore, fixtures, head-to-head, events, lineups, players, transfers, injuries, odds, statistics, and predictions.
- Strengths: good endpoint breadth, clear self-serve pricing, practical for MVPs.
- Tradeoffs: not official; confirm historical seasons, latency, and license terms before commercial use.

Sources:

- https://www.api-football.com/pricing
- https://www.api-football.com/news/post/how-to-get-started-with-api-football-the-complete-beginners-guide

### 8. nflverse / nfldata.org

Best fit: NFL analytics, historical play-by-play, player/team stats, rosters, contracts, combine, and draft data.

- `nfl_data_py` imports play-by-play data back to 1999, weekly data, rosters, schedules, and more.
- nfldata.org exposes public read-only access to the nflverse gold layer via REST endpoints.
- Strengths: excellent free/open NFL analytics source; practical for modeling and historical research.
- Tradeoffs: not an official live commercial feed; licensing and attribution should be reviewed; not the right source for official low-latency game products.

Sources:

- https://github.com/nflverse/nfl_data_py
- https://api.nfldata.org/docs

### 9. ESPN public/hidden endpoints

Best fit: non-critical prototype scoreboards, schedules, teams, rosters, news, summaries.

- Community documentation describes ESPN endpoint patterns for scoreboards, teams, rosters, schedules, standings, game summaries, play-by-play, and news across NBA/NFL and soccer.
- Strengths: free, no auth for many public endpoints, easy to test.
- Tradeoffs: unofficial, unsupported, no SLA, endpoint schemas can change, licensing/redistribution is unclear.

Sources:

- https://github.com/sejaldua/espn-api/blob/main/references/endpoints.md
- https://github.com/jlstewart12/Public-ESPN-API-Fork

### 10. Open football datasets

Best fit: offline historical UEFA/soccer experiments, demos, and analytics notebooks.

- StatsBomb open data provides selected football event/lineup/360 JSON files for research and analysis with attribution requirements.
- openfootball/champions-league provides public-domain UEFA Champions League, Europa League, and Conference League structured text data.
- Strengths: free/open and useful for historical exploration.
- Tradeoffs: not live, incomplete for current production needs, data format/coverage varies.

Sources:

- https://github.com/hudl/open-data
- https://github.com/openfootball/champions-league
- https://openfootball.github.io/

## League-by-League Recommendation

### NBA

Primary production choice: Sportradar NBA API.

Why: it is the most rights-clean and production-ready option found. It supports JSON/XML, API-key auth, official-source NBA data collection, current v8 docs, and deep league-specific feeds.

MVP alternative: BALLDONTLIE or SportsDataIO.

Research-only option: `nba_api` package for NBA.com/stats endpoints. This is useful for internal experiments, but NBA.com terms make it a poor fit for public/commercial database, fantasy, gambling, or live play-by-play products without permission.

### NFL

Primary official-data choice: Genius Sports.

Why: NFL.com identifies Genius Sports as exclusive distributor for official real-time NFL play-by-play, Next Gen Stats, and official betting feeds through the 2027-28 season.

Production alternative: Sportradar NFL v7 or SportsDataIO NFL, depending on licensing, data depth, and budget. Validate whether the license covers the exact product use case.

Research/open option: nflverse/nfldata.org.

### UEFA

Primary production choices: Sportradar Soccer/Soccer Extended or Stats Perform/Opta.

Why: UEFA itself does not appear to offer a public developer API, and UEFA.com terms are restrictive for systematic collection. Licensed soccer data providers are the safer path for commercial use.

Paid MVP alternatives: SportsDataIO Soccer/Global, API-Football, BALLDONTLIE UCL.

Free/lightweight options: football-data.org for Champions League schedules/standings/delayed scores; openfootball/StatsBomb open data for historical datasets.

## Key Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| League/platform terms restrict commercial use | App may be unable to launch legally with scraped or unofficial data | Use licensed vendor for production; review vendor terms before build-out |
| Unofficial endpoints change or block access | Broken scoreboards, missing stats, or outages | Treat as prototype-only; cache and monitor schemas |
| Data latency differs by provider and feed | Live game experience may lag or be inconsistent | Define freshness SLA before selecting vendor |
| ID fragmentation across vendors | Team/player/game IDs will not match across sources | Build a canonical ID mapping table from day one |
| Betting/fantasy rights are more sensitive | Extra legal/product risk | Use vendor feeds explicitly licensed for betting/fantasy |
| Logos/photos/player images have separate rights | UI may violate marks/image restrictions | License images separately or use vendor image/editorial add-ons |

## Proposed Next Steps

1. Confirm product requirements: live vs delayed, historical depth, play-by-play/event data, odds/fantasy, images/logos, and whether "official" is mandatory.
2. Request/test API access:
   - Sportradar trial for NBA and Soccer.
   - Genius Sports sales contact if official NFL data is required.
   - SportsDataIO trial/replay for NBA/NFL/Soccer.
   - BALLDONTLIE/API-Football/football-data.org for low-cost MVP comparison.
3. Run a small integration spike with 3 flows:
   - Daily sync: teams, players, schedules, standings.
   - Live sync: active games/matches, score/game state, box score.
   - Historical sync: last completed season for stats and ID mapping.
4. Build a vendor-neutral internal schema before committing to a provider.
5. Do a legal/licensing check before exposing data publicly or using data in betting/fantasy workflows.

## Practical Shortlist

| Need | Shortlist |
| --- | --- |
| Best official NBA | Sportradar NBA |
| Best official NFL | Genius Sports |
| Best premium UEFA/soccer | Sportradar Soccer/Soccer Extended or Stats Perform/Opta |
| Best single vendor for broad paid MVP | SportsDataIO |
| Best low-cost self-serve MVP | BALLDONTLIE plus API-Football/football-data.org |
| Best free NFL analytics | nflverse/nfldata.org |
| Best free UEFA schedule/results seed data | football-data.org and openfootball |
| Best prototype-only public scoreboards | ESPN endpoints |
