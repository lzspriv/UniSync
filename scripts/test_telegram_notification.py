import argparse
import os
import sys

import requests
from dotenv import load_dotenv


def send_test_message(bot_token: str, chat_id: str, message: str):
    endpoint = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "disable_web_page_preview": True,
    }

    response = requests.post(endpoint, json=payload, timeout=10)
    if response.ok:
        print("Telegram 測試通知已送出。")
        return 0

    print(f"Telegram 測試通知失敗：HTTP {response.status_code}", file=sys.stderr)
    return 1


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="發送 UniSync Telegram 測試通知。")
    parser.add_argument(
        "--message",
        default="UniSync Telegram 測試通知：如果你收到這則訊息，代表通知設定可以使用。",
        help="要送出的測試訊息。",
    )
    args = parser.parse_args()

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    if not bot_token or not chat_id:
        print(
            "缺少 TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID。請先設定環境變數或寫入 .env。",
            file=sys.stderr,
        )
        return 2

    return send_test_message(bot_token, chat_id, args.message)


if __name__ == "__main__":
    raise SystemExit(main())
