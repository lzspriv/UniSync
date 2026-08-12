import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from notifier import (
    build_discord_embed,
    build_telegram_message,
    normalize_notification_url,
)


class NotificationLinkTests(unittest.TestCase):
    def setUp(self):
        self.raw_url = (
            "https://www.epc.ntnu.edu.tw/Front/NEW/Academic/News.aspx?"
            "id=abc&Sn=1374&title=公告 本校EMI課程(第一期)"
        )
        self.announcement = {
            "title": "公告 本校EMI課程",
            "url": self.raw_url,
            "date": "2026-08-12",
        }

    def test_encodes_characters_that_break_markdown_links(self):
        encoded = normalize_notification_url(self.raw_url)

        self.assertNotIn(" ", encoded)
        self.assertNotIn("(", encoded)
        self.assertNotIn(")", encoded)
        self.assertIn("%28%E7%AC%AC%E4%B8%80%E6%9C%9F%29", encoded)
        self.assertIn("&title=", encoded)
        self.assertIn("%E5%85%AC%E5%91%8A%20", encoded)

    def test_preserves_existing_percent_encoding(self):
        encoded = normalize_notification_url("https://example.edu.tw/%E5%85%AC%E5%91%8A?q=a%20b")

        self.assertIn("/%E5%85%AC%E5%91%8A", encoded)
        self.assertIn("q=a%20b", encoded)
        self.assertNotIn("%25E5", encoded)

    def test_discord_embed_uses_encoded_markdown_destination(self):
        embed = build_discord_embed("測試單位-公告", self.announcement)
        encoded = normalize_notification_url(self.raw_url)

        self.assertIn(f"[開啟公告]({encoded})", embed["description"])
        self.assertNotIn(f"[開啟公告]({self.raw_url})", embed["description"])

    def test_telegram_message_uses_encoded_and_html_escaped_url(self):
        message = build_telegram_message("測試單位-公告", self.announcement)
        encoded = normalize_notification_url(self.raw_url).replace("&", "&amp;")

        self.assertIn(f'href="{encoded}"', message)


if __name__ == "__main__":
    unittest.main()
