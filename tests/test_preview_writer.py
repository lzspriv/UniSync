import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from preview_writer import write_category_previews


class PreviewWriterTests(unittest.TestCase):
    def write_existing_preview(self, path, announcements):
        path.write_text(
            json.dumps(
                {
                    "news": {
                        "label": "舊標籤",
                        "announcements": announcements,
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def load_preview(self, path):
        return json.loads(path.read_text(encoding="utf-8"))

    def test_preserves_existing_announcements_on_unexpected_empty_result(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "category-previews.json"
            previous = [{"title": "保留公告", "url": "https://example.com/old"}]
            self.write_existing_preview(output_path, previous)

            write_category_previews(
                {"news": []},
                {"news": "新標籤"},
                output_path,
            )

            preview = self.load_preview(output_path)
            self.assertEqual(preview["news"]["label"], "新標籤")
            self.assertEqual(preview["news"]["announcements"], previous)

    def test_allows_explicitly_empty_category_to_clear_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "category-previews.json"
            self.write_existing_preview(
                output_path,
                [{"title": "舊公告", "url": "https://example.com/old"}],
            )

            write_category_previews(
                {"news": []},
                {"news": "最新消息"},
                output_path,
                allow_empty_category_ids={"news"},
            )

            preview = self.load_preview(output_path)
            self.assertEqual(preview["news"]["announcements"], [])

    def test_replaces_existing_preview_when_scrape_has_results(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "category-previews.json"
            self.write_existing_preview(
                output_path,
                [{"title": "舊公告", "url": "https://example.com/old"}],
            )

            write_category_previews(
                {
                    "news": [
                        {
                            "title": "新公告",
                            "url": "https://example.com/new",
                            "date": "2026-08-05",
                            "date_label": "發布日期",
                        }
                    ]
                },
                {"news": "最新消息"},
                output_path,
            )

            preview = self.load_preview(output_path)
            self.assertEqual(preview["news"]["announcements"][0]["title"], "新公告")
            self.assertFalse(output_path.with_suffix(".json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
