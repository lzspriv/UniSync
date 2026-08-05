from datetime import datetime, timedelta
from urllib.parse import urljoin

from scraper_http import REQUEST_HEADERS, create_request_session
from scraper_parsing import SafeFormatDict, parse_taiwan_date


def fetch_json_announcements(url, category_name, scraper_config):
    try:
        response = create_request_session(url).get(
            url,
            headers=REQUEST_HEADERS,
            timeout=10,
        )
        response.encoding = "utf-8"

        if response.status_code != 200:
            print(f"⚠️ 無法讀取 {category_name}: {response.status_code}")
            return []

        all_news = []
        recent_news = []
        cutoff_date = datetime.now() - timedelta(days=10)
        title_field = scraper_config.get("title_field", "title")
        url_field = scraper_config.get("url_field", "url")
        date_field = scraper_config.get("date_field", "created_time")
        recency_field = scraper_config.get("recency_field", date_field)
        date_label = scraper_config.get("date_label", "發布日期")
        summary_template = scraper_config.get("summary_template")
        include_summary = scraper_config.get("include_summary", False)
        seen_urls = set()

        for item in response.json():
            title = str(item.get(title_field, "")).strip()
            item_url = str(item.get(url_field, "")).strip()
            raw_date = str(item.get(date_field, "")).strip()
            raw_recency_date = str(item.get(recency_field, "")).strip()
            if not title or not item_url:
                continue

            absolute_url = urljoin(url, item_url)
            if absolute_url in seen_urls:
                continue
            seen_urls.add(absolute_url)

            date_text, _ = parse_taiwan_date(raw_date)
            recency_date_text, _ = parse_taiwan_date(raw_recency_date)
            if summary_template:
                summary_text = summary_template.format_map(SafeFormatDict(item)).strip()
            else:
                summary_parts = [
                    str(item.get("place", "")).strip(),
                    str(item.get("start", "")).strip(),
                    str(item.get("end", "")).strip(),
                    f"建立時間：{item.get('created_time', '')}".strip("："),
                ]
                summary_text = " / ".join(part for part in summary_parts if part)

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

            if recency_date_text != "未知日期":
                try:
                    if datetime.strptime(recency_date_text, "%Y-%m-%d") >= cutoff_date:
                        recent_news.append(news_item)
                except ValueError:
                    pass

        return all_news[:5] if len(recent_news) < 5 else recent_news
    except Exception as error:
        print(f"❌ 爬取 {category_name} 時發生異常: {error}")
        return []
