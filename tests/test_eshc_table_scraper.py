import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from scrapers.eshc_table import fetch_eshc_announcements


class EshcTableScraperTests(unittest.TestCase):
    @patch("scrapers.eshc_table.create_request_session")
    def test_converts_fake_future_date_to_pinned_announcement(self, create_session):
        html = """
        <table id="GridView1">
          <tr><th>標題</th><th>日期</th></tr>
          <tr>
            <td><a href="item.aspx?id=1">重要公告</a></td>
            <td>2100/12/31</td>
          </tr>
          <tr>
            <td><a href="item.aspx?id=2">一般公告</a></td>
            <td>2026/07/31</td>
          </tr>
        </table>
        """
        response = Mock(status_code=200, text=html)
        session = Mock()
        session.get.return_value = response
        create_session.return_value = session

        result = fetch_eshc_announcements(
            "https://www.eshc.ntnu.edu.tw/news.aspx",
            "環境安全衛生中心-最新消息",
            {},
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["date"], "未知日期")
        self.assertEqual(result[0]["date_label"], "置頂公告")
        self.assertEqual(
            result[0]["url"],
            "https://www.eshc.ntnu.edu.tw/item.aspx?id=1",
        )
        self.assertEqual(result[1]["date"], "2026-07-31")
        self.assertEqual(result[1]["date_label"], "發布日期")

    @patch("scrapers.eshc_table.create_request_session")
    def test_returns_empty_list_for_http_error(self, create_session):
        response = Mock(status_code=503)
        session = Mock()
        session.get.return_value = response
        create_session.return_value = session

        with patch("builtins.print"):
            result = fetch_eshc_announcements(
                "https://www.eshc.ntnu.edu.tw/news.aspx",
                "環境安全衛生中心-最新消息",
                {},
            )

        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
