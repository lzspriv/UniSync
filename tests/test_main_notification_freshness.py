import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from main import process_pending_announcements, should_notify_announcement


class NotificationFreshnessTests(unittest.TestCase):
    def test_notifies_announcements_within_ten_days(self):
        self.assertTrue(
            should_notify_announcement(
                {"date": "2026-08-01"},
                today=date(2026, 8, 11),
            )
        )

    def test_suppresses_announcements_older_than_ten_days(self):
        self.assertFalse(
            should_notify_announcement(
                {"date": "2026-07-31"},
                today=date(2026, 8, 11),
            )
        )

    def test_keeps_unknown_and_unparseable_dates_eligible(self):
        self.assertTrue(should_notify_announcement({"date": "未知日期"}))
        self.assertTrue(should_notify_announcement({"date": "not-a-date"}))

    @patch("main.notify_announcement_once")
    @patch("main.upsert_announcement_for_categories")
    @patch("main.announcement_exists", return_value=False)
    def test_old_announcements_are_backfilled_without_notification(
        self,
        _announcement_exists,
        upsert_announcement,
        notify_announcement,
    ):
        item = {
            "title": "舊公告",
            "url": "https://example.edu.tw/old",
            "date": "2024-08-28",
        }
        pending = {
            item["url"]: {
                "item": item,
                "categories": {"example_news"},
            }
        }

        dispatched = process_pending_announcements(
            Mock(),
            pending,
            {"example_news": "測試單位-最新消息"},
        )

        self.assertEqual(dispatched, 0)
        upsert_announcement.assert_called_once()
        notify_announcement.assert_not_called()


if __name__ == "__main__":
    unittest.main()
