import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from scrapers.json_events import fetch_json_announcements


class JsonEventsScraperTests(unittest.TestCase):
    @patch("scrapers.json_events.create_request_session")
    def test_maps_fields_deduplicates_urls_and_formats_summary(self, create_session):
        response = Mock()
        response.status_code = 200
        response.json.return_value = [
            {
                "name": "活動一",
                "link": "/events/1",
                "published": "2026-07-31",
                "place": "綜合大樓",
            },
            {
                "name": "重複活動",
                "link": "/events/1",
                "published": "2026-07-31",
                "place": "其他場地",
            },
            {
                "name": "",
                "link": "/events/2",
                "published": "2026-07-31",
            },
        ]
        session = Mock()
        session.get.return_value = response
        create_session.return_value = session

        result = fetch_json_announcements(
            "https://example.edu.tw/api/events",
            "測試單位-活動",
            {
                "title_field": "name",
                "url_field": "link",
                "date_field": "published",
                "summary_template": "地點：{place} {missing}",
                "include_summary": True,
            },
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "活動一")
        self.assertEqual(result[0]["url"], "https://example.edu.tw/events/1")
        self.assertEqual(result[0]["date"], "2026-07-31")
        self.assertEqual(result[0]["summary"], "地點：綜合大樓")
        self.assertTrue(result[0]["show_summary"])
        self.assertEqual(result[0]["category"], "測試單位-活動")

    @patch("scrapers.json_events.create_request_session")
    def test_returns_empty_list_for_http_error(self, create_session):
        response = Mock(status_code=503)
        session = Mock()
        session.get.return_value = response
        create_session.return_value = session

        with patch("builtins.print"):
            result = fetch_json_announcements(
                "https://example.edu.tw/api/events",
                "測試單位-活動",
                {},
            )

        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
