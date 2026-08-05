import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from scrapers.html_cards import fetch_html_announcements


class HtmlCardsScraperTests(unittest.TestCase):
    @patch("scrapers.html_cards.create_request_session")
    def test_default_parser_cleans_suffix_deduplicates_and_skips_old_pin(self, create_session):
        recent_date = datetime.now().strftime("%Y-%m-%d")
        old_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        html = f"""
        <div id="posts">
          <article class="post">
            <h2><a href="/news/1">最新公告 - 網站名稱</a></h2>
            <span class="date">{recent_date} 摘要內容</span>
          </article>
          <article class="post">
            <h2><a href="/news/1">重複公告</a></h2>
            <span class="date">{recent_date}</span>
          </article>
          <article class="post pinned">
            <h2><a href="/news/old">舊置頂公告</a></h2>
            <span class="date">{old_date}</span>
          </article>
        </div>
        """
        response = Mock(status_code=200, text=html)
        session = Mock()
        session.get.return_value = response
        create_session.return_value = session

        result = fetch_html_announcements(
            "https://example.edu.tw/announcements/",
            "測試單位-最新消息",
            {
                "article": "article.post",
                "title_link": "h2 a",
                "date": ".date",
                "strip_title_suffix": " - 網站名稱",
                "pinned": ".pinned",
                "include_summary": True,
            },
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "最新公告")
        self.assertEqual(result[0]["url"], "https://example.edu.tw/news/1")
        self.assertEqual(result[0]["date"], recent_date)
        self.assertEqual(result[0]["summary"], "摘要內容")
        self.assertTrue(result[0]["show_summary"])

    @patch("scrapers.html_cards.create_request_session")
    def test_uses_date_from_url_when_page_has_no_date(self, create_session):
        html = """
        <article class="post">
          <h2><a href="/2026/07/30/news-title/">從網址取得日期</a></h2>
        </article>
        """
        response = Mock(status_code=200, text=html)
        session = Mock()
        session.get.return_value = response
        create_session.return_value = session

        result = fetch_html_announcements(
            "https://example.edu.tw/",
            "測試單位-最新消息",
            {"article": "article.post", "title_link": "h2 a"},
        )

        self.assertEqual(result[0]["date"], "2026-07-30")

    @patch("scrapers.html_cards.create_request_session")
    def test_uses_link_title_when_image_link_has_no_visible_text(self, create_session):
        html = """
        <article class="card">
          <a class="image" href="/news/1" title="圖片公告標題"><img src="cover.png"></a>
          <span class="date">2026-07-31</span>
        </article>
        """
        response = Mock(status_code=200, text=html)
        session = Mock()
        session.get.return_value = response
        create_session.return_value = session

        result = fetch_html_announcements(
            "https://example.edu.tw/",
            "測試單位-最新消息",
            {
                "article": "article.card",
                "title_link": "a.image[title]",
                "date": ".date",
            },
        )

        self.assertEqual(result[0]["title"], "圖片公告標題")
        self.assertEqual(result[0]["url"], "https://example.edu.tw/news/1")

    @patch("scrapers.html_cards.create_request_session")
    def test_dated_link_parser_separates_date_and_title(self, create_session):
        html = '<a class="item" href="/item/1">【2026/07/31】 專題演講</a>'
        response = Mock(status_code=200, text=html)
        session = Mock()
        session.get.return_value = response
        create_session.return_value = session

        result = fetch_html_announcements(
            "https://example.edu.tw/news/",
            "測試單位-活動",
            {
                "parser": "dated_link_list",
                "article": "a.item",
                "title_link": "a.item",
            },
        )

        self.assertEqual(result[0]["date"], "2026-07-31")
        self.assertEqual(result[0]["title"], "專題演講")
        self.assertEqual(result[0]["summary"], "專題演講")


if __name__ == "__main__":
    unittest.main()
