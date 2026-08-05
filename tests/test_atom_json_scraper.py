import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from scrapers.atom_json import fetch_atom_json_announcements


class AtomJsonScraperTests(unittest.TestCase):
    @patch("scrapers.atom_json.create_request_session")
    def test_uses_alternate_link_and_cleans_html_summary(self, create_session):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "feed": {
                "entry": [
                    {
                        "title": {"$t": "  中心   公告  "},
                        "link": [
                            {"rel": "self", "href": "https://api.example/post/1"},
                            {"rel": "alternate", "href": "https://blog.example/post/1"},
                        ],
                        "published": {"$t": "2026-07-31T09:00:00+08:00"},
                        "summary": {"$t": "<p>摘要 <strong>內容</strong></p>"},
                    },
                    {
                        "title": {"$t": "重複公告"},
                        "link": [
                            {"rel": "alternate", "href": "https://blog.example/post/1"},
                        ],
                        "updated": {"$t": "2026-07-30T09:00:00+08:00"},
                    },
                ]
            }
        }
        session = Mock()
        session.get.return_value = response
        create_session.return_value = session

        result = fetch_atom_json_announcements(
            "https://blog.example/",
            "測試中心-最新消息",
            {
                "api_url": "https://api.example/feed.json",
                "date_label": "公告日期",
                "include_summary": True,
            },
        )

        session.get.assert_called_once()
        self.assertEqual(session.get.call_args.args[0], "https://api.example/feed.json")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "中心 公告")
        self.assertEqual(result[0]["url"], "https://blog.example/post/1")
        self.assertEqual(result[0]["date"], "2026-07-31")
        self.assertEqual(result[0]["summary"], "摘要 內容")
        self.assertEqual(result[0]["date_label"], "公告日期")
        self.assertTrue(result[0]["show_summary"])

    @patch("scrapers.atom_json.create_request_session")
    def test_returns_empty_list_for_http_error(self, create_session):
        response = Mock(status_code=500)
        session = Mock()
        session.get.return_value = response
        create_session.return_value = session

        with patch("builtins.print"):
            result = fetch_atom_json_announcements(
                "https://blog.example/",
                "測試中心-最新消息",
                {},
            )

        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
