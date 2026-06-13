from supabase import Client

from announcement_identity import build_announcement_url_candidates, normalize_announcement_url
from date_utils import parse_published_at


def announcement_exists(supabase_client: Client, raw_url: str, cache: dict):
    normalized_url = normalize_announcement_url(raw_url)
    if not normalized_url:
        return False

    if normalized_url in cache:
        return cache[normalized_url]

    for candidate in build_announcement_url_candidates(raw_url):
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


def upsert_announcement_for_categories(supabase_client: Client, item: dict, category_ids: list, category_labels: dict):
    for category_id in category_ids:
        supabase_client.table("announcements").upsert(
            {
                "title": item["title"],
                "url": item["url"],
                "category_id": category_id,
                "source": category_labels.get(category_id, category_id),
                "trigger_type": "menu",
                "published_at": parse_published_at(item.get("date")),
            },
            on_conflict="url,category_id",
        ).execute()
