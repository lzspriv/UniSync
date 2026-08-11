import re
from datetime import datetime, timedelta
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scraper_http import REQUEST_HEADERS, create_request_session
from scraper_parsing import normalize_whitespace, parse_taiwan_date


def fetch_eshc_announcements(url, category_name, scraper_config):
    try:
        response = create_request_session(url).get(url, headers=REQUEST_HEADERS, timeout=10)
        response.encoding = "utf-8"

        if response.status_code != 200:
            print(f"⚠️ 無法讀取 {category_name}: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        all_news = []
        recent_news = []
        cutoff_date = datetime.now() - timedelta(days=10)
        seen_urls = set()

        for row in soup.select(scraper_config.get("article", "#GridView1 tr")):
            link_tag = row.select_one(scraper_config.get("title_link", "a[href*='item.aspx']"))
            if not link_tag or not link_tag.get("href"):
                continue

            title_text = normalize_whitespace(link_tag.get_text(" ", strip=True))
            if not title_text:
                continue

            absolute_url = urljoin(url, link_tag.get("href"))
            if absolute_url in seen_urls:
                continue
            seen_urls.add(absolute_url)

            cells = row.select("td")
            raw_date = normalize_whitespace(cells[-1].get_text(" ", strip=True) if cells else "")
            date_text, _ = parse_taiwan_date(raw_date)
            is_fake_pinned_date = bool(re.match(r"^2100[-/]12[-/]31$", raw_date))
            is_pinned = title_text.startswith("[置頂公告]") or is_fake_pinned_date
            date_label = "置頂公告" if is_pinned else scraper_config.get("date_label", "發布日期")
            if is_fake_pinned_date:
                date_text = "未知日期"

            news_item = {
                "title": title_text,
                "url": absolute_url,
                "date": date_text,
                "date_label": date_label,
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
        print(f"❌ 爬取 {category_name} 時發生錯誤: {error}")
        return []
