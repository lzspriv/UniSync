import json
from datetime import datetime, timedelta
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scraper_http import REQUEST_HEADERS, create_request_session
from scraper_parsing import normalize_whitespace, parse_taiwan_date


def fetch_oia_next_data_announcements(url, category_name, scraper_config):
    try:
        response = create_request_session(url).get(url, headers=REQUEST_HEADERS, timeout=10)
        response.encoding = "utf-8"

        if response.status_code != 200:
            print(f"⚠️ 無法讀取 {category_name}: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        next_data_tag = soup.select_one("#__NEXT_DATA__")
        if not next_data_tag:
            return []

        data = json.loads(next_data_tag.string or "{}")
        items = (
            data.get("props", {})
            .get("pageProps", {})
            .get("pageData", {})
            .get("pta16Data", {})
            .get("highlights", [])
        )

        all_news = []
        recent_news = []
        cutoff_date = datetime.now() - timedelta(days=10)
        seen_urls = set()

        for item in items:
            title = normalize_whitespace(item.get("title", ""))
            news_sno = str(item.get("news_sno", "")).strip()
            raw_date = str(item.get("post_date", "")).strip()
            if not title or not news_sno:
                continue

            absolute_url = urljoin(url, f"{url.rstrip('/')}/{news_sno}")
            if absolute_url in seen_urls:
                continue
            seen_urls.add(absolute_url)

            date_text, _ = parse_taiwan_date(raw_date)
            news_item = {
                "title": title,
                "url": absolute_url,
                "date": date_text,
                "date_label": scraper_config.get("date_label", "發布日期"),
                "summary": "",
                "show_summary": False,
                "category": category_name,
            }
            all_news.append(news_item)

            if date_text != "未知日期":
                try:
                    if datetime.strptime(date_text, "%Y-%m-%d") >= cutoff_date:
                        recent_news.append(news_item)
                except ValueError:
                    pass

        return all_news[:5] if len(recent_news) < 5 else recent_news
    except Exception as error:
        print(f"❌ 爬取 {category_name} 時發生異常: {error}")
        return []
