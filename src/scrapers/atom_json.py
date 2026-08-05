from datetime import datetime, timedelta
from urllib.parse import urljoin

from scraper_http import REQUEST_HEADERS, create_request_session
from scraper_parsing import clean_html_text, normalize_whitespace, parse_taiwan_date


def fetch_atom_json_announcements(url, category_name, scraper_config):
    try:
        feed_url = scraper_config.get("api_url", url)
        response = create_request_session(url).get(
            feed_url,
            headers=REQUEST_HEADERS,
            timeout=10,
        )
        response.encoding = "utf-8"

        if response.status_code != 200:
            print(f"⚠️ 無法讀取 {category_name}: {response.status_code}")
            return []

        data = response.json()
        entries = data.get("feed", {}).get("entry", [])
        all_news = []
        recent_news = []
        cutoff_date = datetime.now() - timedelta(days=10)
        seen_urls = set()
        date_label = scraper_config.get("date_label", "發布日期")
        include_summary = scraper_config.get("include_summary", False)

        for entry in entries:
            title = normalize_whitespace(entry.get("title", {}).get("$t", ""))
            item_url = ""
            for link in entry.get("link", []):
                if link.get("rel") == "alternate" and link.get("href"):
                    item_url = link["href"]
                    break
            if not title or not item_url:
                continue

            absolute_url = urljoin(url, item_url)
            if absolute_url in seen_urls:
                continue
            seen_urls.add(absolute_url)

            raw_date = entry.get("published", {}).get("$t") or entry.get("updated", {}).get("$t", "")
            date_text, _ = parse_taiwan_date(raw_date)
            summary_source = entry.get("summary", {}).get("$t") or entry.get("content", {}).get("$t", "")
            summary_text = clean_html_text(summary_source)

            news_item = {
                "title": title,
                "url": absolute_url,
                "date": date_text,
                "date_label": date_label,
                "summary": summary_text[:150] + "..." if len(summary_text) > 150 else summary_text,
                "show_summary": include_summary,
                "category": category_name,
            }
            all_news.append(news_item)

            if date_text != "?芰?交?":
                try:
                    if datetime.strptime(date_text, "%Y-%m-%d") >= cutoff_date:
                        recent_news.append(news_item)
                except ValueError:
                    pass

        return all_news[:5] if len(recent_news) < 5 else recent_news
    except Exception as error:
        print(f"❌ 爬取 {category_name} 時發生異常: {error}")
        return []
