import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from scrapers.wordpress_rest import fetch_wordpress_rest_announcements


class WordPressRestScraperTests(unittest.TestCase):
    @patch("scrapers.wordpress_rest.create_request_session")
    def test_builds_api_request_cleans_titles_and_deduplicates(self, create_session):
        response = Mock()
        response.status_code = 200
        response.json.return_value = [
            {
                "title": {"rendered": "最新 <strong>公告</strong> &amp; 活動"},
                "link": "https://example.edu.tw/posts/1",
                "date": "2026-07-31T08:00:00",
            },
            {
                "title": {"rendered": "重複公告"},
                "link": "https://example.edu.tw/posts/1",
                "date": "2026-07-30T08:00:00",
            },
        ]
        session = Mock()
        session.get.return_value = response
        create_session.return_value = session

        result = fetch_wordpress_rest_announcements(
            "https://example.edu.tw/category/news/",
            "測試單位-最新消息",
            {"per_page": 7, "categories": 42},
        )

        request_url = session.get.call_args.args[0]
        self.assertIn("/index.php/wp-json/wp/v2/posts?", request_url)
        self.assertIn("per_page=7", request_url)
        self.assertIn("categories=42", request_url)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "最新 公告 & 活動")
        self.assertEqual(result[0]["date"], "2026-07-31")
        self.assertEqual(result[0]["category"], "測試單位-最新消息")

    @patch("scrapers.wordpress_rest.create_request_session")
    def test_returns_empty_list_for_http_error(self, create_session):
        response = Mock(status_code=404)
        session = Mock()
        session.get.return_value = response
        create_session.return_value = session

        with patch("builtins.print"):
            result = fetch_wordpress_rest_announcements(
                "https://example.edu.tw/category/news/",
                "測試單位-最新消息",
                {},
            )

        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
