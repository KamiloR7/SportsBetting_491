from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sportsbetting.collectors.nba import ESPNNBACollector, write_collected_data


TEAMS_PAYLOAD = {
    "sports": [
        {
            "leagues": [
                {
                    "teams": [
                        {
                            "team": {
                                "id": "13",
                                "abbreviation": "LAL",
                                "displayName": "Los Angeles Lakers",
                                "shortDisplayName": "Lakers",
                                "name": "Lakers",
                                "location": "Los Angeles",
                                "color": "552583",
                                "alternateColor": "fdb927",
                                "logos": [{"href": "https://example.test/lakers.png"}],
                            }
                        },
                        {
                            "team": {
                                "id": "9",
                                "abbreviation": "GS",
                                "displayName": "Golden State Warriors",
                                "shortDisplayName": "Warriors",
                                "name": "Warriors",
                                "location": "Golden State",
                            }
                        },
                    ]
                }
            ]
        }
    ]
}


SCOREBOARD_PAYLOAD = {
    "events": [
        {
            "id": "401766122",
            "uid": "s:40~l:46~e:401766122",
            "date": "2026-10-21T02:00Z",
            "name": "Golden State Warriors at Los Angeles Lakers",
            "shortName": "GS @ LAL",
            "season": {"year": 2026, "type": 2},
            "status": {
                "type": {
                    "state": "pre",
                    "name": "STATUS_SCHEDULED",
                    "detail": "Tue, October 20th at 10:00 PM EDT",
                    "completed": False,
                }
            },
            "competitions": [
                {
                    "neutralSite": False,
                    "venue": {
                        "fullName": "Crypto.com Arena",
                        "address": {"city": "Los Angeles", "state": "CA"},
                    },
                    "competitors": [
                        {
                            "homeAway": "home",
                            "score": "0",
                            "team": {
                                "id": "13",
                                "abbreviation": "LAL",
                                "displayName": "Los Angeles Lakers",
                            },
                        },
                        {
                            "homeAway": "away",
                            "score": "0",
                            "team": {
                                "id": "9",
                                "abbreviation": "GS",
                                "displayName": "Golden State Warriors",
                            },
                        },
                    ],
                }
            ],
        }
    ]
}


class ESPNNBACollectorTest(unittest.TestCase):
    def test_collect_teams_normalizes_team_fields(self) -> None:
        collector = ESPNNBACollector(fetcher=_fake_fetcher, retry_backoff_seconds=0)

        teams = collector.collect_teams()

        self.assertEqual(len(teams), 2)
        self.assertEqual(teams[1].source_team_id, "13")
        self.assertEqual(teams[1].display_name, "Los Angeles Lakers")
        self.assertEqual(teams[1].color, "#552583")
        self.assertEqual(teams[1].alternate_color, "#fdb927")
        self.assertEqual(teams[1].logo_url, "https://example.test/lakers.png")

    def test_collect_matches_normalizes_scoreboard_fields(self) -> None:
        collector = ESPNNBACollector(fetcher=_fake_fetcher, retry_backoff_seconds=0)

        matches = collector.collect_matches(date(2026, 10, 20))

        self.assertEqual(len(matches), 1)
        match = matches[0]
        self.assertEqual(match.source_match_id, "401766122")
        self.assertEqual(match.scheduled_at, "2026-10-21T02:00:00Z")
        self.assertEqual(match.season_year, 2026)
        self.assertEqual(match.home_team_abbreviation, "LAL")
        self.assertEqual(match.away_team_abbreviation, "GS")
        self.assertEqual(match.home_score, 0)
        self.assertFalse(match.completed)
        self.assertEqual(match.venue_city, "Los Angeles")

    def test_collect_matches_walks_date_range_and_dedupes_by_match_id(self) -> None:
        calls: list[str] = []

        def fetcher(url: str, timeout: int) -> dict:
            calls.append(url)
            return SCOREBOARD_PAYLOAD if "scoreboard" in url else TEAMS_PAYLOAD

        collector = ESPNNBACollector(fetcher=fetcher, retry_backoff_seconds=0)

        matches = collector.collect_matches(date(2026, 10, 20), date(2026, 10, 21))

        self.assertEqual(len(matches), 1)
        scoreboard_dates = [
            parse_qs(urlparse(call).query)["dates"][0]
            for call in calls
            if "scoreboard" in call
        ]
        self.assertEqual(scoreboard_dates, ["20261020", "20261021"])

    def test_write_collected_data_creates_json_outputs(self) -> None:
        collector = ESPNNBACollector(fetcher=_fake_fetcher, retry_backoff_seconds=0)
        teams = collector.collect_teams()
        matches = collector.collect_matches(date(2026, 10, 20))

        with tempfile.TemporaryDirectory() as temp_dir:
            paths = write_collected_data(Path(temp_dir), teams=teams, matches=matches)

            self.assertTrue(paths["teams"].exists())
            self.assertTrue(paths["matches"].exists())
            self.assertTrue(paths["metadata"].exists())
            self.assertEqual(len(json.loads(paths["teams"].read_text())), 2)
            self.assertEqual(len(json.loads(paths["matches"].read_text())), 1)
            self.assertEqual(json.loads(paths["metadata"].read_text())["source"], "espn")


def _fake_fetcher(url: str, timeout: int) -> dict:
    if url.endswith("/teams?limit=100"):
        return TEAMS_PAYLOAD
    if "scoreboard" in url:
        return SCOREBOARD_PAYLOAD
    raise AssertionError(f"Unexpected URL: {url}")


if __name__ == "__main__":
    unittest.main()
