import json
from pathlib import Path
from scraper import fetch_university_announcements

# 載入配置
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "university-config.json"
with CONFIG_PATH.open("r", encoding="utf-8") as f:
    config = json.load(f)

# 測試 chem_cnews
chem_cnews_config = config["categories"]["chem_cnews"]
url = chem_cnews_config["url"]
label = chem_cnews_config.get("label")
owner = chem_cnews_config.get("owner")
display_name = f"{owner}-{label}"
selectors = chem_cnews_config.get("selectors", None)

print(f"🔍 測試分類：{display_name}")
print(f"📝 URL: {url}")
print(f"📍 Selectors: {selectors}")
print("-" * 80)

news_items = fetch_university_announcements(url, display_name, selectors)

print(f"\n✅ 返回的項目數：{len(news_items)}")
print("\n詳細內容：")
for i, item in enumerate(news_items, 1):
    print(f"\n{i}. 標題：{item.get('title')}")
    print(f"   URL：{item.get('url')}")
    print(f"   日期：{item.get('date')}")
    print(f"   分類：{item.get('category')}")
    print(f"   摘要：{item.get('summary')}")
