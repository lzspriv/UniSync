import logging
import requests
from supabase import Client

def get_subscriptions_for_category(supabase: Client, category_id: str):
    """
    根據 category_id 從資料庫獲取訂閱此類別的使用者 Webhook 列表。
    """
    try:
        # 1. 找到所有訂閱此 category_id 的 user_id
        res_subs = supabase.from_("user_subscriptions").select("user_id").eq("category_id", category_id).execute()
        user_ids = {item['user_id'] for item in res_subs.data}

        if not user_ids:
            return []

        # 2. 根據 user_id 列表，查詢 profiles 表以獲取 discord_webhook
        res_profiles = supabase.from_("profiles").select("discord_webhook").in_("id", list(user_ids)).execute()
        
        # 過濾掉空的 webhook
        webhooks = [item['discord_webhook'] for item in res_profiles.data if item.get('discord_webhook')]
        return webhooks

    except Exception as e:
        logging.error(f"從 Supabase 獲取訂閱時出錯: {e}")
        return []

def format_keyword_badges(keywords: list):
    """
    Discord embed fields 支援 markdown。用 code style 顯示關鍵字，避免被誤認為連結。
    """
    if not keywords:
        return ""
    return " ".join(f"`{keyword}`" for keyword in keywords)


def build_discord_embed(category_label: str, announcement: dict, matched_keywords: list = None):
    """
    Discord 的 embed title 若設定 url，整個 title 都會變成連結。
    因此只把「開啟公告」放成連結，分類與關鍵字放在 fields 中保持純資訊呈現。
    """
    matched_keywords = matched_keywords or []
    announcement_url = announcement.get("url", "")
    date_label = announcement.get("date_label", "發布日期")
    description_lines = [
        announcement.get("title", "(無標題)"),
        f"{date_label}: {announcement.get('date', 'N/A')}",
    ]
    summary = announcement.get("summary") if announcement.get("show_summary") else ""
    if summary:
        description_lines.append(summary)

    if announcement_url:
        description_lines.append(f"[開啟公告]({announcement_url})")

    fields = []
    if category_label:
        fields.append({
            "name": "來源分類",
            "value": category_label,
            "inline": False
        })

    if matched_keywords:
        fields.append({
            "name": "全域關鍵字",
            "value": format_keyword_badges(matched_keywords),
            "inline": False
        })

    embed = {
        "title": "📢 新公告",
        "description": "\n".join(description_lines),
        "color": 15158332 if matched_keywords else 3447003,
    }

    if fields:
        embed["fields"] = fields

    return embed


def send_discord_notification(webhook_url: str, category_id: str, announcements: list, matched_keywords: list = None):
    """
    將新公告發送到指定的 Discord Webhook URL。
    """
    if not announcements:
        return

    # 建立美觀的 Discord Embed 訊息
    embeds = []
    for anno in announcements[:5]: # 最多一次顯示 5 則，避免訊息過長
        embeds.append(build_discord_embed(category_id, anno, matched_keywords))

    payload = {
        "embeds": embeds
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=5)
        response.raise_for_status()
        logging.info(f"成功發送通知到 {webhook_url[:30]}...")
    except requests.RequestException as e:
        logging.warning(f"發送通知到 {webhook_url[:30]}... 失敗: {e}")


def notify_users(supabase: Client, category_id: str, new_announcements: list):
    """
    通知所有訂閱了某個類別的使用者。
    """
    if not new_announcements:
        return False

    webhooks = get_subscriptions_for_category(supabase, category_id)
    
    if not webhooks:
        logging.info(f"類別 [{category_id}] 沒有找到任何有效的訂閱者。")
        return True # 沒有人訂閱，也算處理成功

    logging.info(f"準備將 [{category_id}] 的新公告通知 {len(webhooks)} 位訂閱者...")

    for webhook in webhooks:
        send_discord_notification(webhook, category_id, new_announcements)
        
    return True


def get_subscriptions_for_categories(supabase: Client, category_ids: list):
    """
    根據多個 category_id 合併訂閱者 Webhook，並去重。
    """
    webhook_set = set()
    for category_id in category_ids:
        webhooks = get_subscriptions_for_category(supabase, category_id)
        webhook_set.update(webhooks)
    return list(webhook_set)


def normalize_keywords(raw_keywords):
    """
    將 profiles.keywords 正規化成乾淨的關鍵字陣列。
    """
    if not raw_keywords:
        return []

    if isinstance(raw_keywords, str):
        candidates = [raw_keywords]
    elif isinstance(raw_keywords, list):
        candidates = raw_keywords
    else:
        return []

    seen = set()
    keywords = []
    for keyword in candidates:
        if not isinstance(keyword, str):
            continue
        normalized = keyword.strip()
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            keywords.append(normalized)

    return keywords


def build_keyword_search_text(item: dict, category_ids: list, category_labels: dict):
    """
    全域關鍵字會比對公告標題與公告來源/分類名稱，對齊前端 Live Feed 的 title/source 搜尋邏輯。
    """
    parts = [
        item.get("title", ""),
        item.get("category", ""),
        item.get("source", ""),
    ]
    parts.extend(category_labels.get(cat_id, cat_id) for cat_id in category_ids)
    return " ".join(part for part in parts if part).lower()


def get_global_keyword_subscriptions(
    supabase: Client,
    item: dict,
    category_ids: list,
    category_labels: dict = None
):
    """
    找出全域關鍵字命中的 Discord webhook。
    回傳格式：{webhook_url: [matched_keyword, ...]}
    """
    category_labels = category_labels or {}
    search_text = build_keyword_search_text(item, category_ids, category_labels)
    if not search_text:
        return {}

    try:
        res_profiles = (
            supabase.from_("profiles")
            .select("discord_webhook,keywords")
            .execute()
        )
    except Exception as e:
        logging.error(f"讀取全域關鍵字訂閱者失敗: {e}")
        return {}

    matches_by_webhook = {}
    for profile in res_profiles.data or []:
        webhook = profile.get("discord_webhook")
        if not webhook:
            continue

        matched_keywords = [
            keyword
            for keyword in normalize_keywords(profile.get("keywords"))
            if keyword.lower() in search_text
        ]

        if matched_keywords:
            current = matches_by_webhook.setdefault(webhook, [])
            for keyword in matched_keywords:
                if keyword not in current:
                    current.append(keyword)

    return matches_by_webhook


def notify_announcement_once(supabase: Client, item: dict, category_ids: list, category_labels: dict = None):
    """
    對同一則公告（同 URL）只推播一次：
    - 將多個分類的訂閱者合併
    - 將全域關鍵字命中的訂閱者合併
    - 每個 webhook 僅發送一次
    回傳實際嘗試推播的 webhook 數量。
    """
    if not item or not category_ids:
        return 0

    category_labels = category_labels or {}
    friendly_names = [category_labels.get(cat_id, cat_id) for cat_id in sorted(category_ids)]
    category_label = "\n".join(friendly_names)
    category_webhooks = set(get_subscriptions_for_categories(supabase, category_ids))
    keyword_matches = get_global_keyword_subscriptions(supabase, item, category_ids, category_labels)
    all_webhooks = sorted(category_webhooks | set(keyword_matches.keys()))

    if not all_webhooks:
        logging.info(f"公告 [{item.get('title', 'N/A')}] 在分類 [{category_label}] 沒有有效訂閱者或關鍵字命中。")
        return 0

    logging.info(
        f"準備推播公告 [{item.get('title', 'N/A')}]，分類訂閱 {len(category_webhooks)} 位，"
        f"全域關鍵字命中 {len(keyword_matches)} 位，去重後共 {len(all_webhooks)} 位。"
    )

    send_item = {
        "title": item.get("title", "(無標題)"),
        "url": item.get("url", ""),
        "date": item.get("date", "N/A"),
        "date_label": item.get("date_label", "發布日期"),
        "summary": item.get("summary", "") if item.get("show_summary") else "",
        "show_summary": item.get("show_summary", False)
    }

    for webhook in all_webhooks:
        labels = list(friendly_names)
        matched_keywords = keyword_matches.get(webhook, [])

        send_discord_notification(webhook, "\n".join(labels), [send_item], matched_keywords)

    return len(all_webhooks)
