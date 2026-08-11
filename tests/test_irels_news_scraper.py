import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.parse import quote


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from scrapers.irels_news import fetch_irels_news_announcements


class IrelsNewsScraperTests(unittest.TestCase):
    @patch("scrapers.irels_news.create_request_session")
    def test_reads_news_from_html_fragment(self, create_session):
        fragment = """
        <div class="content">
          <div class="news"><div class="news_content">
            <h5>公告日期：2026.3.26</h5>
            <h3>[得獎資訊] 開發AI學習平台</h3>
            <p>研究成果 <strong>摘要</strong></p>
            <a href="https://news.example/item/1">來源</a>
          </div></div>
          <div class="news"><div class="news_content">
            <h5>公告日期：2025.5.8</h5>
            <h3>[研究成果] 數位轉型</h3>
            <p>第二筆摘要</p>
          </div></div>
        </div>
        """
        response = Mock(status_code=200, text=fragment)
        session = Mock()
        session.get.return_value = response
        create_session.return_value = session

        result = fetch_irels_news_announcements(
            "https://www.irels.ntnu.edu.tw/News",
            "學習科學跨國頂尖研究中心-最新消息",
            {"html_url": "https://www.irels.ntnu.edu.tw/News.zh.html"},
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["date"], "2026-03-26")
        self.assertEqual(result[0]["url"], "https://news.example/item/1")
        self.assertEqual(result[0]["summary"], "研究成果 摘要")
        self.assertTrue(result[0]["show_summary"])
        self.assertEqual(
            result[1]["url"],
            "https://www.irels.ntnu.edu.tw/News#"
            + quote("[研究成果] 數位轉型"),
        )

    @patch("scrapers.irels_news.create_request_session")
    def test_falls_back_to_configured_javascript_source(self, create_session):
        fragment_response = Mock(status_code=404, text="")
        script_response = Mock(
            status_code=200,
            text='''
              { date: "2025.5.8", title: "[研究成果] 跨界合作",
                description: `<p>科技系攜手合作</p>`, content: `<p>完整內容</p>`, }
            ''',
        )
        fragment_session = Mock()
        fragment_session.get.return_value = fragment_response
        script_session = Mock()
        script_session.get.return_value = script_response
        create_session.side_effect = [fragment_session, script_session]

        result = fetch_irels_news_announcements(
            "https://www.irels.ntnu.edu.tw/News",
            "學習科學跨國頂尖研究中心-最新消息",
            {"script_url": "https://www.irels.ntnu.edu.tw/js/news.js"},
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "[研究成果] 跨界合作")
        self.assertEqual(result[0]["date"], "2025-05-08")
        self.assertEqual(result[0]["summary"], "科技系攜手合作")


if __name__ == "__main__":
    unittest.main()
