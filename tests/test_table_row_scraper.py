import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.parse import quote


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from scrapers.table_row import fetch_table_row_announcements


class TableRowScraperTests(unittest.TestCase):
    @patch("scrapers.table_row.create_request_session")
    def test_keeps_recent_pin_skips_old_pin_and_reads_onclick_url(self, create_session):
        recent_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        old_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        regular_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        html = f"""
        <table>
          <tr class="item pinned">
            <td class="headline"><a href="/recent" title="完整置頂標題">標題: 短標題</a></td>
            <td class="date">{recent_date}</td>
          </tr>
          <tr class="item pinned">
            <td class="headline"><a href="/old">舊置頂</a></td>
            <td class="date">{old_date}</td>
          </tr>
          <tr class="item" onclick="window.location.href='/onclick'">
            <td class="headline">Onclick 公告</td>
            <td class="date">{regular_date}</td>
          </tr>
        </table>
        """
        response = Mock(status_code=200, text=html)
        session = Mock()
        session.get.return_value = response
        create_session.return_value = session

        result = fetch_table_row_announcements(
            "https://example.edu.tw/news/",
            "測試單位-公告",
            {
                "article": "tr.item",
                "title": ".headline",
                "title_link": "a[href]",
                "date": ".date",
                "pinned": ".pinned",
                "prefer_title_attr": True,
            },
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["title"], "完整置頂標題")
        self.assertEqual(result[0]["date_label"], "置頂公告")
        self.assertEqual(result[0]["url"], "https://example.edu.tw/recent")
        self.assertEqual(result[1]["title"], "Onclick 公告")
        self.assertEqual(result[1]["url"], "https://example.edu.tw/onclick")

    @patch("scrapers.table_row.create_request_session")
    def test_can_generate_fragment_url_for_rows_without_links(self, create_session):
        html = """
        <div class="item">
          <span class="headline">沒有連結的公告<span class="metadata">發布單位</span><span class="metadata published">2026-07-31</span></span>
        </div>
        """
        response = Mock(status_code=200, text=html)
        session = Mock()
        session.get.return_value = response
        create_session.return_value = session

        result = fetch_table_row_announcements(
            "https://example.edu.tw/news/",
            "測試單位-公告",
            {
                "article": ".item",
                "title": ".headline",
                "title_remove": ".metadata",
                "date": ".published",
                "allow_row_without_link": True,
            },
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0]["url"],
            "https://example.edu.tw/news/#" + quote("沒有連結的公告"),
        )

    @patch("scrapers.table_row.create_request_session")
    def test_can_limit_title_to_text_before_first_break(self, create_session):
        html = """
        <table>
          <tr class="item">
            <td class="date">115.08.01</td>
            <td class="headline">公告主旨<br>第一段說明<br><a href="/guide.pdf">操作說明</a></td>
          </tr>
        </table>
        """
        response = Mock(status_code=200, text=html)
        session = Mock()
        session.get.return_value = response
        create_session.return_value = session

        result = fetch_table_row_announcements(
            "https://example.edu.tw/news/",
            "測試單位-公告",
            {
                "article": "tr.item",
                "title": ".headline",
                "title_link": "a[href]",
                "date": ".date",
                "title_before_break": True,
            },
        )

        self.assertEqual(result[0]["title"], "公告主旨")
        self.assertEqual(result[0]["url"], "https://example.edu.tw/guide.pdf")

    @patch("scrapers.table_row.create_request_session")
    def test_passes_timeout_and_ssl_options_to_request(self, create_session):
        response = Mock(status_code=200, text="<table></table>")
        session = Mock()
        session.get.return_value = response
        create_session.return_value = session

        fetch_table_row_announcements(
            "https://example.edu.tw/news/",
            "測試單位-公告",
            {"timeout": 20, "verify_ssl": False},
        )

        request_kwargs = session.get.call_args.kwargs
        self.assertEqual(request_kwargs["timeout"], 20)
        self.assertFalse(request_kwargs["verify"])


if __name__ == "__main__":
    unittest.main()
