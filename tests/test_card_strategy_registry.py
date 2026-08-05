import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from scrapers.card_strategies import CARD_STRATEGIES


class CardStrategyRegistryTests(unittest.TestCase):
    def test_registers_every_supported_html_card_parser(self):
        self.assertEqual(
            set(CARD_STRATEGIES),
            {
                "dated_link_list",
                "spaced_date_link",
                "mgt_card",
                "row_date_link",
                "link_date_text",
                "alumni_card",
                "split_date_card",
                "ctld_media",
                "cal_news_card",
                "rcemi_article_box",
                "sdgs_elementskit_card",
                "wix_blog_card",
            },
        )


if __name__ == "__main__":
    unittest.main()
