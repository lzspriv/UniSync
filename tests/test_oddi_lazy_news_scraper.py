import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from scrapers.oddi_lazy_news import fetch_oddi_lazy_news_announcements


class OddiLazyNewsScraperTests(unittest.TestCase):
    @patch("scrapers.oddi_lazy_news.create_request_session")
    def test_bootstraps_session_and_reads_selected_tab(self, create_session):
        page_response = Mock(
            status_code=200,
            text="""
            <div class="news" data-currentblocktype="encoded-type"
                 data-currentblockid="encoded-block">
              <button data-lazyloadcontent data-blockid="tab-zero"
                      data-loadingamount="five"></button>
              <button data-lazyloadcontent data-blockid="tab-one"
                      data-loadingamount="five"></button>
            </div>
            """,
        )
        api_response = Mock(status_code=200)
        api_response.json.return_value = {
            "res": "success",
            "Category": "category-token",
            "blockId": "block-token",
            "data": [
                {
                    "title": "  師大附中   公告 ",
                    "NodeId": "node-token",
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "absoultSetTop": [0],
                }
            ],
        }
        session = Mock()
        session.get.side_effect = [page_response, api_response]
        create_session.return_value = session

        result = fetch_oddi_lazy_news_announcements(
            "https://www.hs.ntnu.edu.tw/",
            "附屬高級中學-研習資訊",
            {
                "block_selector": ".news",
                "tab_index": 1,
            },
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "師大附中 公告")
        self.assertIn("a=node-token", result[0]["url"])
        self.assertIn("c=block-token", result[0]["url"])
        self.assertIn("cat=category-token", result[0]["url"])
        api_call = session.get.call_args_list[1]
        self.assertEqual(api_call.kwargs["params"]["NodeId"], "tab-one")
        self.assertEqual(api_call.kwargs["params"]["blocktype"], "encoded-type")

    @patch("scrapers.oddi_lazy_news.create_request_session")
    def test_returns_empty_when_tab_index_is_missing(self, create_session):
        page_response = Mock(
            status_code=200,
            text='<div class="news"><button data-lazyloadcontent></button></div>',
        )
        session = Mock()
        session.get.return_value = page_response
        create_session.return_value = session

        result = fetch_oddi_lazy_news_announcements(
            "https://www.hs.ntnu.edu.tw/",
            "附屬高級中學-公告",
            {"block_selector": ".news", "tab_index": 3},
        )

        self.assertEqual(result, [])
        session.get.assert_called_once()


if __name__ == "__main__":
    unittest.main()
