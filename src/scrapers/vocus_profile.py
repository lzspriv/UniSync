import json
from datetime import datetime, timedelta
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scraper_http import build_request_options, create_request_session
from scraper_parsing import normalize_whitespace, parse_taiwan_date


def _collect_content_entries(value, entries):
    if isinstance(value, dict):
        article = value.get("article")
        if value.get("contentId") and value.get("publishAt") and isinstance(article, dict):
            entries.append(value)
        for child in value.values():
            _collect_content_entries(child, entries)
    elif isinstance(value, list):
        for child in value:
            _collect_content_entries(child, entries)


def fetch_vocus_profile_announcements(url, category_name, scraper_config):
    try:
        response = create_request_session(url, scraper_config).get(
            url,
            **build_request_options(scraper_config),
        )
        response.encoding = "utf-8"
        if response.status_code != 200:
            print(f"⚠️ 無法讀取 {category_name}: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        next_data_tag = soup.select_one("#__NEXT_DATA__")
        if not next_data_tag:
            return []

        payload = json.loads(next_data_tag.string or "{}")
        entries = []
        _collect_content_entries(payload.get("props", {}).get("pageProps", {}), entries)
        entries.sort(key=lambda item: str(item.get("publishAt", "")), reverse=True)

        all_news = []
        recent_news = []
        cutoff_date = datetime.now() - timedelta(days=10)
        seen_content_ids = set()

        for item in entries:
            article = item.get("article", {})
            content_id = str(item.get("contentId") or article.get("_id") or "").strip()
            title = normalize_whitespace(str(article.get("title") or item.get("title") or ""))
            if not content_id or not title or content_id in seen_content_ids:
                continue
            seen_content_ids.add(content_id)

            date_text, _ = parse_taiwan_date(str(item.get("publishAt", "")))
            is_recent = False
            if date_text != "未知日期":
                try:
                    is_recent = datetime.strptime(date_text, "%Y-%m-%d") >= cutoff_date
                except ValueError:
                    pass
            if item.get("hasPinned") and not is_recent:
                continue

            news_item = {
                "title": title,
                "url": urljoin(url, f"/article/{content_id}"),
                "date": date_text,
                "date_label": scraper_config.get("date_label", "發布日期"),
                "summary": "",
                "show_summary": False,
                "category": category_name,
            }
            all_news.append(news_item)
            if is_recent:
                recent_news.append(news_item)

        return all_news[:5] if len(recent_news) < 5 else recent_news
    except Exception as error:
        print(f"❌ 爬取 {category_name} 時發生異常: {error}")
        return []
