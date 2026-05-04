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

def send_discord_notification(webhook_url: str, category_id: str, announcements: list):
    """
    將新公告發送到指定的 Discord Webhook URL。
    """
    if not announcements:
        return

    # 建立美觀的 Discord Embed 訊息
    embeds = []
    for anno in announcements[:5]: # 最多一次顯示 5 則，避免訊息過長
        embeds.append({
            "title": f"📢 {category_id}\n新公告",
            "url": anno['url'],
            "description": f"{anno['title']}\n發布日期: {anno.get('date', 'N/A')}",
            "color": 3447003 # Discord 藍色
        })

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


def notify_announcement_once(supabase: Client, item: dict, category_ids: list, category_labels: dict = None):
    """
    對同一則公告（同 URL）只推播一次：
    - 將多個分類的訂閱者合併
    - 每個 webhook 僅發送一次
    回傳實際嘗試推播的 webhook 數量。
    """
    if not item or not category_ids:
        return 0

    category_labels = category_labels or {}
    friendly_names = [category_labels.get(cat_id, cat_id) for cat_id in sorted(category_ids)]
    category_label = "\n".join(friendly_names)
    webhooks = get_subscriptions_for_categories(supabase, category_ids)

    if not webhooks:
        logging.info(f"公告 [{item.get('title', 'N/A')}] 在分類 [{category_label}] 沒有有效訂閱者。")
        return 0

    logging.info(
        f"準備推播公告 [{item.get('title', 'N/A')}]，分類 [{category_label}]，共 {len(webhooks)} 位訂閱者。"
    )

    send_item = {
        "title": item.get("title", "(無標題)"),
        "url": item.get("url", ""),
        "date": item.get("date", "N/A")
    }

    for webhook in webhooks:
        send_discord_notification(webhook, category_label, [send_item])

    return len(webhooks)
