import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from scrapers.vocus_profile import fetch_vocus_profile_announcements


class VocusProfileScraperTests(unittest.TestCase):
    @patch("scrapers.vocus_profile.create_request_session")
    def test_extracts_and_deduplicates_profile_articles(self, create_session):
        entry = {
            "contentId": "article-id",
            "publishAt": "2026-07-30T10:00:00Z",
            "hasPinned": False,
            "article": {"title": "  中心   演講公告 "},
        }
        payload = {
            "props": {
                "pageProps": {
                    "profile": {"contents": [entry]},
                    "duplicate": entry,
                }
            }
        }
        response = Mock(
            status_code=200,
            text=f'<script id="__NEXT_DATA__">{json.dumps(payload)}</script>',
        )
        session = Mock()
        session.get.return_value = response
        create_session.return_value = session

        result = fetch_vocus_profile_announcements(
            "https://vocus.cc/user/center-id",
            "中國大陸研究中心-最新消息",
            {},
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "中心 演講公告")
        self.assertEqual(result[0]["date"], "2026-07-30")
        self.assertEqual(result[0]["url"], "https://vocus.cc/article/article-id")

    @patch("scrapers.vocus_profile.create_request_session")
    def test_returns_empty_when_next_data_is_missing(self, create_session):
        response = Mock(status_code=200, text="<html></html>")
        session = Mock()
        session.get.return_value = response
        create_session.return_value = session

        result = fetch_vocus_profile_announcements(
            "https://vocus.cc/user/center-id",
            "中國大陸研究中心-最新消息",
            {},
        )

        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
