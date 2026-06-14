import os
import sys
from time import perf_counter

from dotenv import load_dotenv
from supabase import create_client

from announcement_identity import normalize_announcement_url
from announcement_repository import announcement_exists, upsert_announcement_for_categories
from config_loader import load_category_config
from notifier import notify_announcement_once
from preview_writer import write_category_previews
from scraper import fetch_university_announcements


def configure_output_encoding():
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def create_supabase_client():
    load_dotenv()
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    return create_client(supabase_url, supabase_key)


def collect_announcements(category_urls: dict, category_labels: dict, full_categories: dict):
    pending_by_url = {}
    category_previews = {category_id: [] for category_id in category_urls.keys()}
    category_timings = []

    for category_id, category_url in category_urls.items():
        display_name = category_labels.get(category_id, category_id)
        meta = full_categories.get(category_id, {})
        scraper_selectors = meta.get("selectors")

        print(f"🔎 [爬取] {display_name} ({category_id})")
        started_at = perf_counter()
        news_items = fetch_university_announcements(category_url, display_name, scraper_selectors)
        elapsed_seconds = perf_counter() - started_at
        category_timings.append((elapsed_seconds, category_id, display_name, len(news_items)))
        print(f"⏱️ [完成] {display_name}：{len(news_items)} 筆，耗時 {elapsed_seconds:.2f}s")
        category_previews[category_id] = news_items[:5]

        for item in news_items:
            normalized_url = normalize_announcement_url(item.get("url", ""))
            if not normalized_url:
                continue

            if normalized_url not in pending_by_url:
                pending_by_url[normalized_url] = {
                    "item": item,
                    "categories": set(),
                    "normalized_url": normalized_url,
                }
            pending_by_url[normalized_url]["categories"].add(category_id)

    return pending_by_url, category_previews, category_timings


def print_scrape_summary(category_timings: list):
    if not category_timings:
        print("📊 爬取摘要：沒有分類需要爬取。")
        return

    total_seconds = sum(item[0] for item in category_timings)
    total_items = sum(item[3] for item in category_timings)
    slowest = sorted(category_timings, reverse=True)[:5]

    print(
        f"📊 爬取摘要：{len(category_timings)} 個分類，"
        f"共 {total_items} 筆候選公告，分類累計耗時 {total_seconds:.2f}s。"
    )
    print("🐢 最慢分類 Top 5：")
    for elapsed_seconds, category_id, display_name, item_count in slowest:
        print(f"   - {display_name} ({category_id})：{elapsed_seconds:.2f}s，{item_count} 筆")


def process_pending_announcements(supabase_client, pending_by_url: dict, category_labels: dict):
    total_dispatched = 0
    existing_count = 0
    new_count = 0
    announcement_exists_cache = {}

    for data in pending_by_url.values():
        item = data["item"]
        categories = sorted(data["categories"])
        category_names = [category_labels.get(category_id, category_id) for category_id in categories]

        is_new_url = not announcement_exists(supabase_client, item.get("url", ""), announcement_exists_cache)
        if not is_new_url:
            existing_count += 1
            continue

        upsert_announcement_for_categories(supabase_client, item, categories, category_labels)
        new_count += 1
        print(f"✨ [新公告] {item['title']} ({', '.join(category_names)})")

        dispatched_count = notify_announcement_once(supabase_client, item, categories, category_labels)
        total_dispatched += dispatched_count

    print(
        f"📬 公告處理摘要：{len(pending_by_url)} 筆唯一公告，"
        f"{existing_count} 筆已存在，{new_count} 筆新公告。"
    )
    return total_dispatched


def run_sync():
    configure_output_encoding()
    sync_started_at = perf_counter()
    category_urls, category_labels, full_categories = load_category_config()
    supabase_client = create_supabase_client()

    print("🚀 UniSync 開始同步...")
    pending_by_url, category_previews, category_timings = collect_announcements(
        category_urls,
        category_labels,
        full_categories,
    )
    print_scrape_summary(category_timings)

    total_dispatched = process_pending_announcements(
        supabase_client,
        pending_by_url,
        category_labels,
    )

    preview_path = write_category_previews(category_previews, category_labels)
    sync_elapsed_seconds = perf_counter() - sync_started_at
    print(f"📄 預覽資料已寫入：{preview_path}")
    print(f"✅ 同步完成，共觸發 {total_dispatched} 次推播，總耗時 {sync_elapsed_seconds:.2f}s。")


if __name__ == "__main__":
    run_sync()
