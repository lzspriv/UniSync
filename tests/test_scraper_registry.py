import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import scraper
from scrapers.registry import SCRAPER_REGISTRY, get_scraper


class ScraperRegistryTests(unittest.TestCase):
    def test_registers_every_standalone_parser(self):
        self.assertEqual(
            set(SCRAPER_REGISTRY),
            {
                "json_events",
                "atom_json",
                "irels_news",
                "wordpress_rest",
                "oia_next_data",
                "eshc_table",
                "table_row",
            },
        )
        for parser_name in SCRAPER_REGISTRY:
            self.assertIsNotNone(get_scraper(parser_name))

    @patch("scraper.get_scraper")
    def test_dispatches_registered_parser(self, get_registered_scraper):
        registered_scraper = Mock(return_value=[{"title": "公告"}])
        get_registered_scraper.return_value = registered_scraper

        result = scraper.fetch_university_announcements(
            "https://example.edu.tw/api",
            "測試單位-公告",
            {"parser": "json_events"},
        )

        self.assertEqual(result, [{"title": "公告"}])
        registered_scraper.assert_called_once_with(
            "https://example.edu.tw/api",
            "測試單位-公告",
            {"parser": "json_events"},
        )

    @patch("scraper.fetch_html_announcements")
    @patch("scraper.get_scraper", return_value=None)
    def test_falls_back_to_html_parser(self, _get_registered_scraper, html_scraper):
        html_scraper.return_value = []

        scraper.fetch_university_announcements(
            "https://example.edu.tw/news/",
            "測試單位-公告",
            None,
        )

        config = html_scraper.call_args.args[2]
        self.assertEqual(config["article"], "#blog-entries article")
        self.assertEqual(config["title_link"], ".blog-entry-title.entry-title a")
        self.assertEqual(config["date"], ".meta-date")


if __name__ == "__main__":
    unittest.main()
