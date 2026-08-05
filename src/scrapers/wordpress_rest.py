from datetime import datetime, timedelta
from urllib.parse import urlencode, urlparse

from scraper_http import REQUEST_HEADERS, create_request_session
from scraper_parsing import clean_html_text, parse_taiwan_date


def fetch_wordpress_rest_announcements(url, category_name, scraper_config):
    try:
        api_url = scraper_config.get("api_url")
        if not api_url:
            parsed_url = urlparse(url)
            api_url = f"{parsed_url.scheme}://{parsed_url.netloc}/index.php/wp-json/wp/v2/posts"

        query = {
            "per_page": scraper_config.get("per_page", 20),
            "orderby": "date",
            "order": "desc",
            "_fields": "date,link,title",
        }
        categories = scraper_config.get("categories")
        if categories:
            query["categories"] = categories

        separator = "&" if "?" in api_url else "?"
        response = create_request_session(api_url).get(
            f"{api_url}{separator}{urlencode(query)}",
            headers=REQUEST_HEADERS,
            timeout=10,
        )

        if response.status_code != 200:
            print(f"⚠️ 無法讀取 {category_name}: {response.status_code}")
            return []

        all_news = []
        recent_news = []
        cutoff_date = datetime.now() - timedelta(days=10)
        seen_urls = set()

        for item in response.json():
            title_text = clean_html_text(item.get("title", {}).get("rendered", ""))
            absolute_url = item.get("link", "")
            if not title_text or not absolute_url or absolute_url in seen_urls:
                continue
            seen_urls.add(absolute_url)

            date_text, _ = parse_taiwan_date(str(item.get("date", "")))
            news_item = {
                "title": title_text,
                "url": absolute_url,
                "date": date_text,
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
