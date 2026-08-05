import sys
import unittest
from pathlib import Path

from bs4 import BeautifulSoup


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import scraper


class ScraperParsingBaselineTests(unittest.TestCase):
    def test_parse_taiwan_date_supports_ad_chinese_date(self):
        date_text, summary = scraper.parse_taiwan_date(
            "公告日期：2026年3月26日 得獎資訊"
        )

        self.assertEqual(date_text, "2026-03-26")
        self.assertEqual(summary, "公告日期： 得獎資訊")

    def test_parse_taiwan_date_supports_roc_date(self):
        date_text, summary = scraper.parse_taiwan_date("🏷️ 115年4月29日 招生公告")

        self.assertEqual(date_text, "2026-04-29")
        self.assertEqual(summary, "招生公告")

    def test_parse_taiwan_date_supports_ad_numeric_date(self):
        date_text, summary = scraper.parse_taiwan_date("2026/04/30 最新消息")

        self.assertEqual(date_text, "2026-04-30")
        self.assertEqual(summary, "最新消息")

    def test_parse_dated_link_text_separates_title(self):
        result = scraper.parse_dated_link_text("【2026/05/11】 專題演講")

        self.assertEqual(result, ("2026-05-11", "專題演講"))

    def test_parse_link_leading_date_removes_repeated_dates(self):
        result = scraper.parse_link_leading_date(
            "2026-05-11 | 2026-05-10 | 公告標題"
        )

        self.assertEqual(result, ("2026-05-11", "公告標題"))

    def test_parse_date_from_url_supports_wordpress_paths(self):
        result = scraper.parse_date_from_url(
            "https://example.edu.tw/2026/05/29/announcement/"
        )

        self.assertEqual(result, "2026-05-29")

    def test_article_matches_class_id_and_tag_selectors(self):
        soup = BeautifulSoup(
            '<article id="important" class="post pinned"></article>',
            "html.parser",
        )
        article = soup.article

        self.assertTrue(scraper.article_matches_selector(article, ".pinned"))
        self.assertTrue(scraper.article_matches_selector(article, "#important"))
        self.assertTrue(scraper.article_matches_selector(article, "article"))
        self.assertFalse(scraper.article_matches_selector(article, ".normal"))


class ScraperHttpBaselineTests(unittest.TestCase):
    def test_build_request_options_uses_defaults(self):
        options = scraper.build_request_options()

        self.assertEqual(options["timeout"], 10)
        self.assertIs(options["headers"], scraper.REQUEST_HEADERS)
        self.assertNotIn("verify", options)

    def test_build_request_options_accepts_timeout_and_ssl_override(self):
        options = scraper.build_request_options(
            {"timeout": 20, "verify_ssl": False}
        )

        self.assertEqual(options["timeout"], 20)
        self.assertFalse(options["verify"])

    def test_create_request_session_uses_legacy_adapter_only_for_pr_site(self):
        legacy_session = scraper.create_request_session("https://pr.ntnu.edu.tw/news/")
        normal_session = scraper.create_request_session("https://www.ntnu.edu.tw/")

        self.assertIsInstance(
            legacy_session.adapters["https://pr.ntnu.edu.tw"],
            scraper.LegacySSLAdapter,
        )
        self.assertNotIsInstance(
            normal_session.adapters["https://"],
            scraper.LegacySSLAdapter,
        )


if __name__ == "__main__":
    unittest.main()
