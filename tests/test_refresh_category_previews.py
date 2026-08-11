import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from refresh_category_previews import refresh_previews


class RefreshCategoryPreviewsTests(unittest.TestCase):
    def test_updates_preview_with_limited_scraped_items(self):
        categories = {"news": {"url": "https://example.com/news", "selectors": {}}}
        labels = {"news": "Example-News"}
        previews = {"news": {"label": "Old", "announcements": [{"title": "Old"}]}}
        items = [
            {
                "title": f"News {index}",
                "url": f"https://example.com/{index}",
                "date": "2026-08-01",
                "date_label": "Published",
                "summary": "Hidden by default",
            }
            for index in range(4)
        ]

        refreshed, results = refresh_previews(
            ["news"],
            labels,
            categories,
            previews,
            fetcher=lambda *_args: items,
            max_items=2,
        )

        self.assertEqual(results, [("news", "updated", "2 preview items")])
        self.assertEqual([item["title"] for item in refreshed["news"]["announcements"]], ["News 0", "News 1"])
        self.assertEqual(refreshed["news"]["announcements"][0]["summary"], "")

    def test_preserves_existing_preview_on_unexpected_empty_result(self):
        categories = {"news": {"url": "https://example.com/news"}}
        previews = {"news": {"label": "Existing", "announcements": [{"title": "Keep me"}]}}

        refreshed, results = refresh_previews(
            ["news"],
            {"news": "Example-News"},
            categories,
            previews,
            fetcher=lambda *_args: [],
        )

        self.assertEqual(refreshed, previews)
        self.assertEqual(results[0][1], "unexpected_empty")

    def test_allows_empty_preview_for_explicitly_empty_category(self):
        categories = {"news": {"url": "https://example.com/news", "allowEmpty": True}}

        refreshed, results = refresh_previews(
            ["news"],
            {"news": "Example-News"},
            categories,
            {},
            fetcher=lambda *_args: [],
        )

        self.assertEqual(refreshed["news"]["announcements"], [])
        self.assertEqual(results, [("news", "updated", "0 preview items")])


if __name__ == "__main__":
    unittest.main()
