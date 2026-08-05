import unittest

from scripts.check_all_sources import classify_status, group_categories, validate_items


class CheckAllSourcesTests(unittest.TestCase):
    def test_groups_same_domain_sequentially(self):
        categories = {
            "a": {"url": "https://example.edu.tw/news"},
            "b": {"url": "https://example.edu.tw/events"},
            "c": {"url": "https://other.edu.tw/news"},
        }

        groups = group_categories(["a", "b", "c"], categories)

        self.assertIn(["a", "b"], groups)
        self.assertIn(["c"], groups)

    def test_validates_required_announcement_fields(self):
        problems = validate_items([{"title": "", "url": "/relative", "date": ""}])

        self.assertEqual(
            problems,
            ["item 1: missing title", "item 1: invalid URL", "item 1: missing date"],
        )

    def test_distinguishes_expected_and_unexpected_empty_sources(self):
        self.assertEqual(classify_status([], [], True), "expected_empty")
        self.assertEqual(classify_status([], [], False), "unexpected_empty")
        self.assertEqual(classify_status([{"title": "News"}], [], False), "ok")


if __name__ == "__main__":
    unittest.main()
