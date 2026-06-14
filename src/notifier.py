import logging
from html import escape as escape_html

import requests
from supabase import Client


PROFILE_NOTIFICATION_COLUMNS = "discord_webhook,telegram_bot_token,telegram_chat_id"
PROFILE_NOTIFICATION_KEYWORD_COLUMNS = f"{PROFILE_NOTIFICATION_COLUMNS},keywords"


def _clean_value(value):
    if value is None:
        return ""
    return str(value).strip()


def _merge_keyword_matches(target_map: dict, target, matched_keywords: list):
    current = target_map.setdefault(target, [])
    for keyword in matched_keywords:
        if keyword not in current:
            current.append(keyword)


def get_profile_notification_targets(profile: dict):
    targets = {
        "discord": set(),
        "telegram": set(),
    }

    discord_webhook = _clean_value(profile.get("discord_webhook"))
    if discord_webhook:
        targets["discord"].add(discord_webhook)

    telegram_bot_token = _clean_value(profile.get("telegram_bot_token"))
    telegram_chat_id = _clean_value(profile.get("telegram_chat_id"))
    if telegram_bot_token and telegram_chat_id:
        targets["telegram"].add((telegram_bot_token, telegram_chat_id))

    return targets


def merge_notification_targets(base: dict, incoming: dict):
    for channel in ("discord", "telegram"):
        base.setdefault(channel, set()).update(incoming.get(channel, set()))
    return base


def empty_notification_targets():
    return {
        "discord": set(),
        "telegram": set(),
    }


def fetch_profiles(supabase: Client, user_ids=None, include_keywords=False):
    columns = PROFILE_NOTIFICATION_KEYWORD_COLUMNS if include_keywords else PROFILE_NOTIFICATION_COLUMNS
    query = supabase.from_("profiles").select(columns)
    if user_ids is not None:
        query = query.in_("id", list(user_ids))

    try:
        return query.execute()
    except Exception as e:
        logging.warning(f"讀取 Telegram 欄位失敗，暫時退回 Discord 欄位: {e}")
        fallback_columns = "discord_webhook,keywords" if include_keywords else "discord_webhook"
        query = supabase.from_("profiles").select(fallback_columns)
        if user_ids is not None:
            query = query.in_("id", list(user_ids))
        return query.execute()

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
        res_profiles = fetch_profiles(supabase, user_ids)
        
        # 過濾掉空的 webhook
        webhooks = [item['discord_webhook'] for item in res_profiles.data if item.get('discord_webhook')]
        return webhooks

    except Exception as e:
        logging.error(f"從 Supabase 獲取訂閱時出錯: {e}")
        return []


def get_notification_targets_for_category(supabase: Client, category_id: str):
    """
    根據 category_id 取得 Discord 與 Telegram 通知目標。
    """
    try:
        res_subs = supabase.from_("user_subscriptions").select("user_id").eq("category_id", category_id).execute()
        user_ids = {item["user_id"] for item in res_subs.data}

        if not user_ids:
            return empty_notification_targets()

        res_profiles = fetch_profiles(supabase, user_ids)
        targets = empty_notification_targets()
        for profile in res_profiles.data or []:
            merge_notification_targets(targets, get_profile_notification_targets(profile))
        return targets

    except Exception as e:
        logging.error(f"從 Supabase 獲取通知目標時出錯: {e}")
        return empty_notification_targets()

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
        logging.info("成功發送 Discord 通知")
    except requests.RequestException as e:
        status_code = getattr(getattr(e, "response", None), "status_code", None)
        detail = f"HTTP {status_code}" if status_code else e.__class__.__name__
        logging.warning(f"Discord 通知發送失敗: {detail}")


def truncate_text(value: str, limit: int = 600):
    if not value:
        return ""
    value = str(value).strip()
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def build_telegram_message(category_label: str, announcement: dict, matched_keywords: list = None):
    matched_keywords = matched_keywords or []
    title = truncate_text(announcement.get("title", "(無標題)"), 300)
    url = _clean_value(announcement.get("url", ""))
    date_label = announcement.get("date_label", "發布日期")
    summary = announcement.get("summary") if announcement.get("show_summary") else ""

    lines = ["📢 <b>新公告</b>"]

    if category_label:
        lines.extend(["", "<b>來源分類</b>", escape_html(category_label)])

    if matched_keywords:
        keyword_badges = " ".join(f"<code>{escape_html(keyword)}</code>" for keyword in matched_keywords)
        lines.extend(["", "<b>全域關鍵字</b>", keyword_badges])

    lines.append("")
    if url:
        lines.append(f"<a href=\"{escape_html(url, quote=True)}\">{escape_html(title)}</a>")
    else:
        lines.append(f"<b>{escape_html(title)}</b>")

    lines.append(f"{escape_html(date_label)}: {escape_html(str(announcement.get('date', 'N/A')))}")

    if summary:
        lines.extend(["", escape_html(truncate_text(summary, 700))])

    message = "\n".join(lines)
    return truncate_text(message, 4000)


def send_telegram_notification(bot_token: str, chat_id: str, category_id: str, announcements: list, matched_keywords: list = None):
    """
    使用 Telegram Bot API 將新公告送到指定 chat_id。
    """
    if not bot_token or not chat_id or not announcements:
        return

    endpoint = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    for anno in announcements[:5]:
        payload = {
            "chat_id": chat_id,
            "text": build_telegram_message(category_id, anno, matched_keywords),
            "parse_mode": "HTML",
            "link_preview_options": {"is_disabled": True},
        }

        try:
            response = requests.post(endpoint, json=payload, timeout=8)
            response.raise_for_status()
            logging.info(f"成功發送 Telegram 通知到 chat_id={chat_id}")
        except requests.RequestException as e:
            status_code = getattr(getattr(e, "response", None), "status_code", None)
            detail = f"HTTP {status_code}" if status_code else e.__class__.__name__
            logging.warning(f"Telegram 通知發送失敗: {detail}")


def notify_users(supabase: Client, category_id: str, new_announcements: list):
    """
    通知所有訂閱了某個類別的使用者。
    """
    if not new_announcements:
        return False

    targets = get_notification_targets_for_category(supabase, category_id)
    
    if not targets["discord"] and not targets["telegram"]:
        logging.info(f"類別 [{category_id}] 沒有找到任何有效的訂閱者。")
        return True # 沒有人訂閱，也算處理成功

    total_targets = len(targets["discord"]) + len(targets["telegram"])
    logging.info(f"準備將 [{category_id}] 的新公告通知 {total_targets} 個接收目標...")

    for webhook in sorted(targets["discord"]):
        send_discord_notification(webhook, category_id, new_announcements)

    for bot_token, chat_id in sorted(targets["telegram"]):
        send_telegram_notification(bot_token, chat_id, category_id, new_announcements)
        
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


def get_notification_targets_for_categories(supabase: Client, category_ids: list):
    """
    根據多個 category_id 合併 Discord 與 Telegram 通知目標，並去重。
    """
    targets = empty_notification_targets()
    for category_id in category_ids:
        merge_notification_targets(targets, get_notification_targets_for_category(supabase, category_id))
    return targets


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
    找出全域關鍵字命中的通知目標。
    回傳格式：
    {
        "discord": {webhook_url: [matched_keyword, ...]},
        "telegram": {(bot_token, chat_id): [matched_keyword, ...]}
    }
    """
    category_labels = category_labels or {}
    search_text = build_keyword_search_text(item, category_ids, category_labels)
    if not search_text:
        return {"discord": {}, "telegram": {}}

    try:
        res_profiles = fetch_profiles(supabase, include_keywords=True)
    except Exception as e:
        logging.error(f"讀取全域關鍵字訂閱者失敗: {e}")
        return {"discord": {}, "telegram": {}}

    matches = {
        "discord": {},
        "telegram": {},
    }
    for profile in res_profiles.data or []:
        matched_keywords = [
            keyword
            for keyword in normalize_keywords(profile.get("keywords"))
            if keyword.lower() in search_text
        ]

        if matched_keywords:
            profile_targets = get_profile_notification_targets(profile)
            for webhook in profile_targets["discord"]:
                _merge_keyword_matches(matches["discord"], webhook, matched_keywords)
            for telegram_target in profile_targets["telegram"]:
                _merge_keyword_matches(matches["telegram"], telegram_target, matched_keywords)

    return matches


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
    category_targets = get_notification_targets_for_categories(supabase, category_ids)
    keyword_matches = get_global_keyword_subscriptions(supabase, item, category_ids, category_labels)
    discord_targets = sorted(category_targets["discord"] | set(keyword_matches["discord"].keys()))
    telegram_targets = sorted(category_targets["telegram"] | set(keyword_matches["telegram"].keys()))
    total_targets = len(discord_targets) + len(telegram_targets)

    if total_targets == 0:
        logging.info(f"公告 [{item.get('title', 'N/A')}] 在分類 [{category_label}] 沒有有效訂閱者或關鍵字命中。")
        return 0

    logging.info(
        f"準備推播公告 [{item.get('title', 'N/A')}]，"
        f"分類訂閱 Discord {len(category_targets['discord'])} 個、Telegram {len(category_targets['telegram'])} 個，"
        f"全域關鍵字命中 Discord {len(keyword_matches['discord'])} 個、Telegram {len(keyword_matches['telegram'])} 個，"
        f"去重後共 {total_targets} 個接收目標。"
    )

    send_item = {
        "title": item.get("title", "(無標題)"),
        "url": item.get("url", ""),
        "date": item.get("date", "N/A"),
        "date_label": item.get("date_label", "發布日期"),
        "summary": item.get("summary", "") if item.get("show_summary") else "",
        "show_summary": item.get("show_summary", False)
    }

    for webhook in discord_targets:
        labels = list(friendly_names)
        matched_keywords = keyword_matches["discord"].get(webhook, [])

        send_discord_notification(webhook, "\n".join(labels), [send_item], matched_keywords)

    for bot_token, chat_id in telegram_targets:
        matched_keywords = keyword_matches["telegram"].get((bot_token, chat_id), [])
        send_telegram_notification(bot_token, chat_id, "\n".join(friendly_names), [send_item], matched_keywords)

    return total_targets
