from datetime import datetime, timedelta
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup

from scraper_http import build_request_options, create_request_session
from scraper_parsing import normalize_whitespace, parse_taiwan_date


def _is_active_pinned(item):
    if item.get("SetTopStatus"):
        return True
    absolute_set_top = item.get("absoultSetTop") or []
    return bool(absolute_set_top and str(absolute_set_top[0]).lower() in {"1", "true"})


def fetch_oddi_lazy_news_announcements(url, category_name, scraper_config):
    try:
        session = create_request_session(url, scraper_config)
        request_options = build_request_options(scraper_config)
        page_response = session.get(url, **request_options)
        page_response.encoding = "utf-8"
        if page_response.status_code != 200:
            print(f"⚠️ 無法讀取 {category_name}: {page_response.status_code}")
            return []

        soup = BeautifulSoup(page_response.text, "html.parser")
        block = soup.select_one(scraper_config["block_selector"])
        if not block:
            return []

        buttons = block.select("button[data-lazyloadcontent]")
        tab_index = int(scraper_config.get("tab_index", 0))
        if tab_index < 0 or tab_index >= len(buttons):
            return []
        button = buttons[tab_index]

        params = {
            "LoadingAmount": button.get("data-loadingamount", ""),
            "NodeId": button.get("data-blockid", ""),
            "categorystate": button.get("data-categorystate", ""),
            "blocktype": block.get("data-currentblocktype", ""),
            "blockId": block.get("data-currentblockid", ""),
            "CurrentUsers": "",
            "SpecialRequirements": button.get("data-special-requirements", ""),
        }
        api_response = session.get(
            urljoin(url, "/lazyloadnews"),
            params=params,
            **request_options,
        )
        if api_response.status_code != 200:
            print(f"⚠️ 無法讀取 {category_name} API: {api_response.status_code}")
            return []

        payload = api_response.json()
        if payload.get("res") != "success":
            return []

        all_news = []
        recent_news = []
        cutoff_date = datetime.now() - timedelta(days=10)
        old_articles_count = 0
        seen_urls = set()
        unknown_date, _ = parse_taiwan_date("")
        category_token = payload.get("Category", "")
        block_token = payload.get("blockId", "")

        for item in payload.get("data", []):
            title = normalize_whitespace(str(item.get("title", "")))
            node_id = str(item.get("NodeId", "")).strip()
            if not title or not node_id:
                continue

            query = urlencode(
                {
                    "a": node_id,
                    "c": block_token,
                    "cat": category_token,
                }
            )
            detail_url = f"{urljoin(url, '/content')}?{query}"
            if detail_url in seen_urls:
                continue
            seen_urls.add(detail_url)

            date_text, _ = parse_taiwan_date(str(item.get("time", "")))
            is_recent = False
            date_is_known = date_text != unknown_date
            if date_is_known:
                try:
                    is_recent = datetime.strptime(date_text, "%Y-%m-%d") >= cutoff_date
                except ValueError:
                    date_is_known = False

            if _is_active_pinned(item) and not is_recent:
                continue

            news_item = {
                "title": title,
                "url": detail_url,
                "date": date_text,
                "date_label": scraper_config.get("date_label", "發布日期"),
                "summary": "",
                "show_summary": False,
                "category": category_name,
            }
            all_news.append(news_item)

            if is_recent:
                recent_news.append(news_item)
                old_articles_count = 0
            else:
                old_articles_count += 1
                if date_is_known and len(all_news) >= 10 and old_articles_count >= 5:
                    break

        return all_news[:5] if len(recent_news) < 5 else recent_news
    except Exception as error:
        print(f"❌ 爬取 {category_name} 時發生異常: {error}")
        return []
