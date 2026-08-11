import re
from datetime import datetime, timedelta
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup

from date_utils import UNKNOWN_DATE
from scraper_http import REQUEST_HEADERS, create_request_session
from scraper_parsing import clean_html_text, normalize_whitespace, parse_taiwan_date


def fetch_irels_news_announcements(url, category_name, scraper_config):
    try:
        date_label = scraper_config.get("date_label", "發布日期")
        cutoff_date = datetime.now() - timedelta(days=10)
        all_news = []
        recent_news = []
        seen_urls = set()

        html_url = scraper_config.get("html_url") or urljoin(url, "News.zh.html")
        html_response = create_request_session(html_url).get(
            html_url,
            headers=REQUEST_HEADERS,
            timeout=10,
        )
        html_response.encoding = "utf-8"

        if html_response.status_code == 200 and "<html" not in html_response.text[:200].lower():
            soup = BeautifulSoup(html_response.text, "html.parser")
            for article in soup.select(".content .news, .news"):
                content = article.select_one(".news_content") or article
                title_tag = content.select_one("h3")
                if not title_tag:
                    continue

                title = normalize_whitespace(title_tag.get_text(" ", strip=True))
                if not title:
                    continue

                raw_date = content.select_one("h5")
                date_text, _ = parse_taiwan_date(raw_date.get_text(" ", strip=True) if raw_date else "")
                summary_tag = content.select_one("p")
                summary_text = clean_html_text(str(summary_tag)) if summary_tag else ""
                source_link = next(
                    (
                        link
                        for link in content.select("a[href]")
                        if link.get("href", "").strip().startswith("http")
                    ),
                    None,
                )
                item_url = source_link.get("href").strip() if source_link else f"{url}#{quote(title[:80])}"
                item_url = urljoin(url, item_url)
                if item_url in seen_urls:
                    continue
                seen_urls.add(item_url)

                news_item = {
                    "title": title,
                    "url": item_url,
                    "date": date_text,
                    "date_label": date_label,
                    "summary": summary_text[:150] + "..." if len(summary_text) > 150 else summary_text,
                    "show_summary": bool(summary_text),
                    "category": category_name,
                }
                all_news.append(news_item)

                if date_text != "未知日期":
                    try:
                        if datetime.strptime(date_text, "%Y-%m-%d") >= cutoff_date:
                            recent_news.append(news_item)
                    except ValueError:
                        pass

            if all_news:
                return all_news[:5] if len(recent_news) < 5 else recent_news

        script_url = scraper_config.get("script_url")
        if not script_url:
            page_response = create_request_session(url).get(
                url,
                headers=REQUEST_HEADERS,
                timeout=10,
            )
            page_response.encoding = "utf-8"
            if page_response.status_code != 200:
                print(f"⚠️ 無法讀取 {category_name}: {page_response.status_code}")
                return []

            page_soup = BeautifulSoup(page_response.text, "html.parser")
            news_script = page_soup.select_one('script[src*="news"]')
            if not news_script or not news_script.get("src"):
                print(f"⚠️ 找不到 {category_name} 的 news script")
                return []
            script_url = urljoin(url, news_script.get("src"))

        response = create_request_session(script_url).get(
            script_url,
            headers=REQUEST_HEADERS,
            timeout=10,
        )
        response.encoding = "utf-8"

        if response.status_code != 200:
            print(f"⚠️ 無法讀取 {category_name}: {response.status_code}")
            return []

        pattern = re.compile(
            r'\{\s*date:\s*"(?P<date>[^"]+)"\s*,\s*'
            r'title:\s*"(?P<title>(?:\\.|[^"])*)".*?'
            r"description:\s*`(?P<description>.*?)`\s*,\s*"
            r"content:\s*`(?P<content>.*?)`\s*,",
            re.S,
        )
        for match in pattern.finditer(response.text):
            title = normalize_whitespace(match.group("title").replace('\\"', '"'))
            if not title:
                continue
            item_url = f"{url}#{quote(title[:80])}"
            if item_url in seen_urls:
                continue
            seen_urls.add(item_url)

            date_text, _ = parse_taiwan_date(match.group("date"))
            summary_text = clean_html_text(match.group("description") or match.group("content"))

            news_item = {
                "title": title,
                "url": item_url,
                "date": date_text,
                "date_label": date_label,
                "summary": summary_text[:150] + "..." if len(summary_text) > 150 else summary_text,
                "show_summary": bool(summary_text),
                "category": category_name,
            }
            all_news.append(news_item)

            if date_text != UNKNOWN_DATE:
                try:
                    if datetime.strptime(date_text, "%Y-%m-%d") >= cutoff_date:
                        recent_news.append(news_item)
                except ValueError:
                    pass

        return all_news[:5] if len(recent_news) < 5 else recent_news
    except Exception as error:
        print(f"❌ 爬取 {category_name} 時發生異常: {error}")
        return []
