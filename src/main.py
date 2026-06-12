import os
import json
from pathlib import Path
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit
from dotenv import load_dotenv
from supabase import create_client, Client
from scraper import fetch_university_announcements
from notifier import notify_announcement_once

# 1. 初始化環境變數與 Supabase
load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "university-config.json"


def load_category_config():
    """
    從單一 JSON 設定檔載入分類 URL 與中文顯示名稱。
    """
    with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    categories = config.get("categories", {})
    csie_categories = {category_id: meta.get("url", "") for category_id, meta in categories.items()}
    category_labels = {
        category_id: (
            f"{meta.get('owner', '')}-{meta.get('label', category_id)}"
            if meta.get("owner")
            else meta.get("label", category_id)
        )
        for category_id, meta in categories.items()
    }
    return csie_categories, category_labels, categories


# 2. 從共用設定檔載入掃描清單與中文標籤
CSIE_CATEGORIES, CATEGORY_LABELS, FULL_CATEGORIES = load_category_config()


def parse_published_at(date_str: str):
    if not date_str:
        return None

    date_text = date_str.strip()
    if date_text in ("未知日期", ""):
        return None

    # 支援 YYYY-MM-DD 轉 ISO
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_text, fmt).isoformat()
        except ValueError:
            continue
    return None


def normalize_announcement_url(raw_url: str):
    """
    將公告 URL 正規化，避免尾斜線或 fragment 造成重複判定。
    保留 query string，因為它通常包含區分公告的唯一標識符（如 id）。
    """
    if not raw_url:
        return ""

    parsed = urlsplit(raw_url.strip())
    path = parsed.path.rstrip("/")
    if not path:
        path = "/"
    
    # 保留 query string 以正確區分有相同路徑但不同 ID 的公告
    query = parsed.query

    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, query, ""))


def announcement_exists(supabase_client: Client, raw_url: str, cache: dict):
    """
    判斷公告是否已存在。會同時檢查原始 URL 與正規化 URL，並以快取避免重複查詢。
    """
    normalized_url = normalize_announcement_url(raw_url)
    if not normalized_url:
        return False

    if normalized_url in cache:
        return cache[normalized_url]

    candidates = []
    if raw_url:
        candidates.append(raw_url)
    if normalized_url != raw_url:
        candidates.append(normalized_url)

    for candidate in candidates:
        existing = (
            supabase_client.table("announcements")
            .select("id")
            .eq("url", candidate)
            .limit(1)
            .execute()
        )
        if existing.data:
            cache[normalized_url] = True
            return True

    cache[normalized_url] = False
    return False

def run_sync():
    print("🚀 UniSync 多使用者同步引擎啟動...")
    total_dispatched = 0
    # 以 URL 聚合新公告，避免同一篇被多分類重複推播
    pending_by_url = {}
    announcement_exists_cache = {}
    # 記錄每個分類的所有公告用於預覽
    category_previews = {cat_id: [] for cat_id in CSIE_CATEGORIES.keys()}

    for cat_id, cat_url in CSIE_CATEGORIES.items():
        # 友善顯示名稱（中文）
        display_name = CATEGORY_LABELS.get(cat_id, cat_id)
        
        # ✨ 修正：從完整設定中抓出對應分類的 selectors
        meta = FULL_CATEGORIES.get(cat_id, {})
        scraper_selectors = meta.get("selectors", None)

        print(f"🔍 掃描分類：{display_name} ({cat_id})")
        news_items = fetch_university_announcements(cat_url, display_name, scraper_selectors)
        
        # 記錄該分類爬到的所有公告（用於預覽）
        category_previews[cat_id] = news_items[:5]  # 每個分類保留最新 5 篇用於預覽
        
        for item in news_items:
            normalized_url = normalize_announcement_url(item.get('url', ''))
            if not normalized_url:
                continue

            if normalized_url not in pending_by_url:
                pending_by_url[normalized_url] = {
                    "item": item,
                    "categories": set(),
                    "normalized_url": normalized_url
                }
            pending_by_url[normalized_url]["categories"].add(cat_id)

    # 第二階段：每個 URL 僅通知一次；資料庫則按 category_id 存一筆，供 Live Feed 查詢
    for _, data in pending_by_url.items():
        item = data["item"]
        categories = sorted(data["categories"])
        category_names = [CATEGORY_LABELS.get(cat_id, cat_id) for cat_id in categories]
        normalized_url = data.get("normalized_url", normalize_announcement_url(item.get("url", "")))

        # 1. 檢查這個 URL 是否首次出現（用於「是否推播」判斷）
        is_new_url = not announcement_exists(supabase, item.get("url", ""), announcement_exists_cache)

        if not is_new_url:
            print(f"↩️ [已存在] {item['title']} ({', '.join(category_names)})")
            continue

        # 2. 每個分類各存一筆，確保 Live Feed 可依 category_id 精準查詢
        for cat_id in categories:
            supabase.table("announcements").upsert(
                {
                    "title": item['title'],
                    "url": item['url'],
                    "category_id": cat_id,
                    "source": CATEGORY_LABELS.get(cat_id, cat_id),
                    "trigger_type": "menu",
                    "published_at": parse_published_at(item.get("date"))
                },
                on_conflict="url,category_id"
            ).execute()

        print(f"✨ [新公告] {item['title']} ({', '.join(category_names)})")

        # 3. 只有首次出現的 URL 才觸發推播（避免重複通知）
        if is_new_url:
            dispatched_count = notify_announcement_once(supabase, item, categories, CATEGORY_LABELS)
            total_dispatched += dispatched_count
    
    # 第三階段：生成預覽 JSON 供前端使用
    preview_data = {}
    for cat_id, items in category_previews.items():
        preview_data[cat_id] = {
            "label": CATEGORY_LABELS.get(cat_id, cat_id),
            "announcements": [
                {
                    "title": item.get("title", "(無標題)"),
                    "url": item.get("url", ""),
                    "date": item.get("date", "未知日期")
                }
                for item in items
            ]
        }
    
    # 寫入預覽檔案到專案根目錄
    preview_path = Path(__file__).resolve().parent.parent / "category-previews.json"
    with preview_path.open("w", encoding="utf-8") as f:
        json.dump(preview_data, f, ensure_ascii=False, indent=2)
    print(f"📋 預覽資料已生成：{preview_path}")
    
    print(f"✅ 同步完成！共觸發 {total_dispatched} 次推播。")

if __name__ == "__main__":
    run_sync()