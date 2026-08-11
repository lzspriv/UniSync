import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from scrapers.oia_next_data import fetch_oia_next_data_announcements


class OiaNextDataScraperTests(unittest.TestCase):
    @patch("scrapers.oia_next_data.create_request_session")
    def test_extracts_highlights_and_builds_detail_urls(self, create_session):
        payload = {
            "props": {
                "pageProps": {
                    "pageData": {
                        "pta16Data": {
                            "highlights": [
                                {
                                    "title": "  國際   交流公告 ",
                                    "news_sno": 123,
                                    "post_date": "2026-07-31",
                                },
                                {
                                    "title": "重複公告",
                                    "news_sno": 123,
                                    "post_date": "2026-07-30",
                                },
                                {
                                    "title": "缺少編號",
                                    "post_date": "2026-07-29",
                                },
                            ]
                        }
                    }
                }
            }
        }
        response = Mock(
            status_code=200,
            text=f'<html><script id="__NEXT_DATA__" type="application/json">{json.dumps(payload)}</script></html>',
        )
        session = Mock()
        session.get.return_value = response
        create_session.return_value = session

        result = fetch_oia_next_data_announcements(
            "https://bds.oia.ntnu.edu.tw/bds/web/news-intcoop",
            "國際事務處-國際交流",
            {"date_label": "公告日期"},
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "國際 交流公告")
        self.assertEqual(
            result[0]["url"],
            "https://bds.oia.ntnu.edu.tw/bds/web/news-intcoop/123",
        )
        self.assertEqual(result[0]["date"], "2026-07-31")
        self.assertEqual(result[0]["date_label"], "公告日期")

    @patch("scrapers.oia_next_data.create_request_session")
    def test_returns_empty_list_when_next_data_is_missing(self, create_session):
        response = Mock(status_code=200, text="<html><body></body></html>")
        session = Mock()
        session.get.return_value = response
        create_session.return_value = session

        result = fetch_oia_next_data_announcements(
            "https://bds.oia.ntnu.edu.tw/bds/web/news-intcoop",
            "國際事務處-國際交流",
            {},
        )

        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
