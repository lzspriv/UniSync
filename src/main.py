import os
import json
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
from scraper import fetch_ntnu_csie_category
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
    return csie_categories, category_labels


# 2. 從共用設定檔載入掃描清單與中文標籤
CSIE_CATEGORIES, CATEGORY_LABELS = load_category_config()

def run_sync():
    print("🚀 UniSync 多使用者同步引擎啟動...")
    total_dispatched = 0
    # 以 URL 聚合新公告，避免同一篇被多分類重複推播
    pending_by_url = {}
    # 記錄每個分類的所有公告用於預覽
    category_previews = {cat_id: [] for cat_id in CSIE_CATEGORIES.keys()}

    for cat_id, cat_url in CSIE_CATEGORIES.items():
        # 友善顯示名稱（中文）
        display_name = CATEGORY_LABELS.get(cat_id, cat_id)
        
        print(f"🔍 掃描分類：{display_name} ({cat_id})")
        news_items = fetch_ntnu_csie_category(cat_url, display_name)
        
        # 記錄該分類爬到的所有公告（用於預覽）
        category_previews[cat_id] = news_items[:5]  # 每個分類保留最新 5 篇用於預覽
        
        for item in news_items:
            # 檢查資料庫是否已存過此 URL
            check = supabase.table("announcements").select("id").eq("url", item['url']).execute()
            
            if len(check.data) == 0:
                if item['url'] not in pending_by_url:
                    pending_by_url[item['url']] = {
                        "item": item,
                        "categories": set()
                    }
                pending_by_url[item['url']]["categories"].add(cat_id)

    # 第二階段：每個 URL 只通知一次，由 notifier 統一處理推播
    for url_key, data in pending_by_url.items():
        item = data["item"]
        categories = sorted(data["categories"])
        category_names = [CATEGORY_LABELS.get(cat_id, cat_id) for cat_id in categories]

        # 1. 存入公告紀錄表（同 URL 只插入一次）
        supabase.table("announcements").insert({
            "title": item['title'],
            "url": item['url'],
            "source": f"資工系辦 - {', '.join(category_names)}"
        }).execute()

        print(f"✨ [新公告] {item['title']}")

        # 2. 合併此公告所有分類的訂閱者，去重後只推播一次
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