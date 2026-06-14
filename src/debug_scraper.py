from pathlib import Path

from config_loader import load_category_config
from scraper import fetch_university_announcements


CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "university-config.json"
DEBUG_CATEGORY_ID = "chem_cnews"


category_urls, category_labels, categories = load_category_config(CONFIG_PATH)
category_config = categories[DEBUG_CATEGORY_ID]
url = category_urls[DEBUG_CATEGORY_ID]
display_name = category_labels[DEBUG_CATEGORY_ID]
selectors = category_config.get("selectors")

print(f"Testing category: {display_name}")
print(f"URL: {url}")
print(f"Selectors: {selectors}")
print("-" * 80)

news_items = fetch_university_announcements(url, display_name, selectors)

print(f"\nFetched announcements: {len(news_items)}")
for index, item in enumerate(news_items, 1):
    print(f"\n{index}. Title: {item.get('title')}")
    print(f"   URL: {item.get('url')}")
    print(f"   Date: {item.get('date')}")
    print(f"   Category: {item.get('category')}")
    print(f"   Summary: {item.get('summary')}")
