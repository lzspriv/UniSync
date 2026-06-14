import requests
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import re
import ssl
from urllib.parse import quote, urlencode, urljoin, urlparse
from html import unescape


REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
}


class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = ssl.create_default_context()
        context.set_ciphers("DEFAULT@SECLEVEL=1")
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)


def article_matches_selector(article, selector):
    if not selector:
        return False

    if selector.startswith("."):
        return selector[1:] in article.get("class", [])

    if selector.startswith("#"):
        return article.get("id") == selector[1:]

    return article.name == selector


def parse_taiwan_date(text):
    """
    智慧解析字串中的日期（支援民國、西元格式）。
    成功則回傳 "YYYY-MM-DD"，失敗回傳 "未知日期"。
    """
    if not text:
        return "未知日期", text
        
    # 🔍 尋找西元中文格式，例如: 2026 年 6 月 12 日
    ad_zh_match = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', text)
    if ad_zh_match:
        year, month, day = ad_zh_match.groups()
        summary = text.replace(ad_zh_match.group(0), "").strip()
        return f"{year}-{int(month):02d}-{int(day):02d}", summary

    # 🔍 尋找民國格式，例如: 115年4月29日 或 114年12月15日
    tw_match = re.search(r'(?<!\d)(\d{2,3})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', text)
    if tw_match:
        year = int(tw_match.group(1)) + 1911  # 轉為西元年
        month = int(tw_match.group(2))
        day = int(tw_match.group(3))
        # 將原本文字中的日期標籤部分拿掉，保留純內文當摘要
        summary = text.replace(tw_match.group(0), "").replace("🏷️", "").strip()
        return f"{year}-{month:02d}-{day:02d}", summary

    # 🔍 尋找西元格式，例如: 2026-04-30、2026/04/30、2026.04.30
    en_match = re.search(r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', text)
    if en_match:
        summary = text.replace(en_match.group(0), "").strip()
        return f"{en_match.group(1)}-{int(en_match.group(2)):02d}-{int(en_match.group(3)):02d}", summary

    # Some Oen sites render dates as 2025-09/30.
    hybrid_match = re.search(r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', text.replace("/", "-"))
    if hybrid_match:
        summary = text.replace(hybrid_match.group(0), "").strip()
        return (
            f"{hybrid_match.group(1)}-{int(hybrid_match.group(2)):02d}-{int(hybrid_match.group(3)):02d}",
            summary,
        )

    # Ultimate Post grids often render dates as 6 月 14, 2026.
    zh_comma_match = re.search(r'(\d{1,2})\s*月\s*(\d{1,2})\s*,\s*((?:19|20)\d{2})', text)
    if zh_comma_match:
        month, day, year = zh_comma_match.groups()
        summary = text.replace(zh_comma_match.group(0), "").strip()
        return f"{year}-{int(month):02d}-{int(day):02d}", summary

    zh_month_match = re.search(r'(\d{4})\s*(?:年)?\s*(\d{1,2})\s*月\s*(\d{1,2})\s*(?:日)?', text)
    if zh_month_match:
        year, month, day = zh_month_match.groups()
        summary = text.replace(zh_month_match.group(0), "").strip()
        return f"{year}-{int(month):02d}-{int(day):02d}", summary

    return "未知日期", text


def normalize_whitespace(text):
    return re.sub(r"\s+", " ", text or "").strip()


def parse_dated_link_text(text):
    """
    Parse list links that include the publish date in the link text, for example:
    [2026/05/11] Title
    """
    if not text:
        return "未知日期", ""

    match = re.match(
        r"^\s*[\[【(（]?\s*(\d{4})[-/](\d{1,2})[-/](\d{1,2})\s*[\]】)）]?\s*(.+?)\s*$",
        text,
    )
    if match:
        year, month, day, title = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}", title.strip()

    date_text, summary_text = parse_taiwan_date(text)
    return date_text, summary_text.strip()


def parse_spaced_date_link_text(text):
    match = re.match(r"^\s*((?:19|20)\d{2})\s+(\d{1,2})\s+(\d{1,2})\s+(.+?)\s*$", text or "")
    if not match:
        return "未知日期", ""

    year, month, day, title = match.groups()
    try:
        date_text = datetime(int(year), int(month), int(day)).strftime("%Y-%m-%d")
    except ValueError:
        return "未知日期", ""

    return date_text, title.strip()


def parse_mgt_card_article(article, fallback_title):
    year_tag = article.select_one(".news-list-date .year")
    month_tag = article.select_one(".news-list-date .month")
    day_tag = article.select_one(".news-list-date .date")
    title_tag = article.select_one(".news-list-text")

    if year_tag and month_tag and day_tag:
        year_match = re.search(r"(?:19|20)\d{2}", year_tag.get_text(" ", strip=True))
        month_match = re.search(r"\d{1,2}", month_tag.get_text(" ", strip=True))
        day_match = re.search(r"\d{1,2}", day_tag.get_text(" ", strip=True))
        if year_match and month_match and day_match:
            try:
                date_text = datetime(
                    int(year_match.group(0)),
                    int(month_match.group(0)),
                    int(day_match.group(0)),
                ).strftime("%Y-%m-%d")
            except ValueError:
                date_text = "未知日期"
            else:
                title_text = normalize_whitespace(
                    title_tag.get_text(" ", strip=True) if title_tag else fallback_title
                )
                return date_text, title_text

    return parse_spaced_date_link_text(fallback_title)


def parse_alumni_date(text):
    if not text:
        return "未知日期"

    match = re.search(r"(\d{1,2})\s+(\d{4})\.(\d{1,2})", text.strip())
    if not match:
        return "未知日期"

    day, year, month = match.groups()
    return f"{year}-{int(month):02d}-{int(day):02d}"


def parse_leading_date(text):
    if not text:
        return "未知日期", text

    match = re.match(r"^\s*(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", text)
    if match:
        year, month, day = match.groups()
        summary = text[match.end():].lstrip(" |｜-—\t")
        return f"{year}-{int(month):02d}-{int(day):02d}", summary

    return parse_taiwan_date(text)


def parse_link_leading_date(text):
    date_text, summary_text = parse_leading_date(text)
    while date_text != "未知日期":
        next_date_text, next_summary_text = parse_leading_date(summary_text)
        if next_date_text == "未知日期":
            break
        summary_text = next_summary_text
    return date_text, normalize_whitespace(summary_text)


def parse_date_from_url(value):
    parsed_url = urlparse(value or "")
    match = re.search(r"/((?:19|20)\d{2})/(\d{1,2})/(\d{1,2})(?:/|$)", parsed_url.path)
    if not match:
        return "未知日期"

    year, month, day = (int(part) for part in match.groups())
    try:
        return datetime(year, month, day).strftime("%Y-%m-%d")
    except ValueError:
        return "未知日期"


def parse_yearless_month_day(text):
    match = re.search(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日", text or "")
    if not match:
        return "未知日期"

    now = datetime.now()
    month, day = (int(part) for part in match.groups())
    try:
        parsed = datetime(now.year, month, day)
    except ValueError:
        return "未知日期"

    if parsed.date() > now.date():
        try:
            parsed = datetime(now.year - 1, month, day)
        except ValueError:
            return "未知日期"

    return parsed.strftime("%Y-%m-%d")


def extract_onclick_url(onclick_text):
    if not onclick_text:
        return ""
    match = re.search(
        r"(?:location(?:\.href)?|window\.location(?:\.href)?)\s*=\s*['\"]([^'\"]+)['\"]",
        onclick_text,
    )
    return match.group(1).strip() if match else ""


def parse_split_date(yearmonth_text, day_text):
    match = re.search(r"(\d{4})[-/.](\d{1,2})", yearmonth_text or "")
    day_match = re.search(r"(\d{1,2})", day_text or "")
    if not match or not day_match:
        return "未知日期"

    year, month = match.groups()
    day = day_match.group(1)
    return f"{year}-{int(month):02d}-{int(day):02d}"


def parse_cal_date(date_tag):
    if not date_tag:
        return "未知日期"

    date_text = date_tag.get_text(" ", strip=True)
    parsed_date, _ = parse_taiwan_date(date_text)
    if parsed_date != "未知日期":
        return parsed_date

    month_map = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }
    day_tag = date_tag.select_one(".day")
    month_tag = date_tag.select_one(".month")
    day_match = re.search(r"\d{1,2}", day_tag.get_text(" ", strip=True) if day_tag else "")
    month_text = (month_tag.get_text(" ", strip=True) if month_tag else "")[:3].lower()

    if not day_match or month_text not in month_map:
        return "未知日期"

    today = datetime.now()
    candidate = datetime(today.year, month_map[month_text], int(day_match.group(0)))
    if candidate - today > timedelta(days=30):
        candidate = candidate.replace(year=today.year - 1)

    return candidate.strftime("%Y-%m-%d")


class SafeFormatDict(dict):
    def __missing__(self, key):
        return ""


def create_request_session(url):
    session = requests.Session()
    if urlparse(url).netloc.lower() == "pr.ntnu.edu.tw":
        session.mount("https://pr.ntnu.edu.tw", LegacySSLAdapter())
    return session


def fetch_json_announcements(url, category_name, scraper_config):
    try:
        response = create_request_session(url).get(
            url,
            headers=REQUEST_HEADERS,
            timeout=10,
        )
        response.encoding = 'utf-8'

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
                "category": category_name
            }
            all_news.append(news_item)

            if recency_date_text != "未知日期":
                try:
                    if datetime.strptime(recency_date_text, "%Y-%m-%d") >= cutoff_date:
                        recent_news.append(news_item)
                except ValueError:
                    pass

        return all_news[:5] if len(recent_news) < 5 else recent_news
    except Exception as e:
        print(f"❌ 爬取 {category_name} 時發生異常: {e}")
        return []


def clean_html_text(value):
    text = BeautifulSoup(value or "", "html.parser").get_text(" ", strip=True)
    return normalize_whitespace(unescape(text))


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
    except Exception as e:
        print(f"❌ 爬取 {category_name} 時發生異常: {e}")
        return []


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
    except Exception as e:
        print(f"❌ 爬取 {category_name} 時發生異常: {e}")
        return []


def parse_rcemi_article(article, fallback_title):
    title_tag = article.select_one(".article h3")
    if not title_tag:
        return "未知日期", "", ""

    title_text = normalize_whitespace(title_tag.get_text(" ", strip=True))
    date_row = article.select_one(".date-row")
    if date_row:
        date_text, _ = parse_taiwan_date(date_row.get_text(" ", strip=True))
    else:
        date_text = parse_split_date(
            article.select_one(".date .month").get_text(" ", strip=True)
            if article.select_one(".date .month")
            else "",
            article.select_one(".date .day").get_text(" ", strip=True)
            if article.select_one(".date .day")
            else "",
        )

    summary_tag = article.select_one(".article p")
    summary_text = summary_tag.get_text(" ", strip=True) if summary_tag else ""
    return date_text, title_text or fallback_title, summary_text


def parse_sdgs_card_article(article, fallback_title):
    title_tag = article.select_one(".entry-title a")
    title_text = normalize_whitespace(title_tag.get_text(" ", strip=True) if title_tag else fallback_title)

    date_text = "\u672a\u77e5\u65e5\u671f"
    date_tag = article.select_one(".elementskit-meta-lists")
    if date_tag:
        date_source = normalize_whitespace(date_tag.get_text(" ", strip=True))
        match = re.search(r"(\d{1,2})\s+(\d{1,2})\s*\u6708", date_source)
        if match:
            day, month = (int(part) for part in match.groups())
            today = datetime.now()
            try:
                candidate = datetime(today.year, month, day)
                if candidate.date() > today.date():
                    candidate = candidate.replace(year=today.year - 1)
                date_text = candidate.strftime("%Y-%m-%d")
            except ValueError:
                pass

    summary_tag = article.select_one(".elementskit-post-body p")
    summary_text = normalize_whitespace(summary_tag.get_text(" ", strip=True) if summary_tag else "")
    return date_text, title_text, summary_text


def fetch_eshc_announcements(url, category_name, scraper_config):
    try:
        response = create_request_session(url).get(url, headers=REQUEST_HEADERS, timeout=10)
        response.encoding = "utf-8"

        if response.status_code != 200:
            print(f"\u26a0\ufe0f \u7121\u6cd5\u8b80\u53d6 {category_name}: {response.status_code}")
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
            is_pinned = title_text.startswith("[\u7f6e\u9802\u516c\u544a]") or is_fake_pinned_date
            date_label = "\u7f6e\u9802\u516c\u544a" if is_pinned else scraper_config.get("date_label", "\u767c\u5e03\u65e5\u671f")
            if is_fake_pinned_date:
                date_text = "\u672a\u77e5\u65e5\u671f"

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

            if date_text != "\u672a\u77e5\u65e5\u671f":
                try:
                    if datetime.strptime(date_text, "%Y-%m-%d") >= cutoff_date:
                        recent_news.append(news_item)
                except ValueError:
                    pass

        return all_news[:5] if len(recent_news) < 5 else recent_news
    except Exception as e:
        print(f"\u274c \u722c\u53d6 {category_name} \u6642\u767c\u751f\u932f\u8aa4: {e}")
        return []


def fetch_table_row_announcements(url, category_name, scraper_config):
    try:
        response = create_request_session(url).get(url, headers=REQUEST_HEADERS, timeout=10)
        response.encoding = "utf-8"

        if response.status_code != 200:
            print(f"?? ?⊥?霈??{category_name}: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        all_news = []
        recent_news = []
        cutoff_date = datetime.now() - timedelta(days=10)
        old_articles_count = 0
        seen_urls = set()
        unknown_date, _ = parse_taiwan_date("")
        pinned_selector = scraper_config.get("pinned")
        include_summary = scraper_config.get("include_summary", False)
        date_label = scraper_config.get("date_label", "?澆??交?")

        for article in soup.select(scraper_config.get("article", "tr")):
            title_tag = None
            title_selector = scraper_config.get("title")
            if title_selector:
                title_tag = article.select_one(title_selector)

            link_selector = scraper_config.get("title_link", "a[href]")
            link_tag = article.select_one(link_selector)
            if not title_tag:
                title_tag = link_tag

            title_text = normalize_whitespace(
                title_tag.get_text(" ", strip=True) if title_tag else ""
            )
            if not title_text:
                continue

            href = link_tag.get("href", "").strip() if link_tag and link_tag.get("href") else ""
            if not href:
                href = extract_onclick_url(article.get("onclick", ""))
            if not href and scraper_config.get("allow_row_without_link"):
                href = f"#{quote(title_text[:80])}"
            if not href:
                continue

            absolute_url = urljoin(url, href)
            if absolute_url in seen_urls:
                continue
            seen_urls.add(absolute_url)

            date_selector = scraper_config.get("date")
            date_tag = article.select_one(date_selector) if date_selector else None
            raw_date_text = (
                date_tag.get_text(" ", strip=True)
                if date_tag
                else article.get_text(" ", strip=True)
            )
            date_text, summary_text = parse_taiwan_date(raw_date_text)
            if date_text == unknown_date:
                date_text, summary_text = parse_leading_date(raw_date_text)

            is_pinned = bool(
                pinned_selector
                and (
                    article_matches_selector(article, pinned_selector)
                    or article.select_one(pinned_selector)
                )
            )
            item_date_label = "\u7f6e\u9802\u516c\u544a" if is_pinned else date_label
            is_recent = False
            date_is_known = date_text != unknown_date
            if date_is_known:
                try:
                    article_date = datetime.strptime(date_text, "%Y-%m-%d")
                    is_recent = article_date >= cutoff_date
                except ValueError:
                    date_is_known = False

            if is_pinned and not is_recent:
                continue

            news_item = {
                "title": title_text,
                "url": absolute_url,
                "date": date_text,
                "date_label": item_date_label,
                "summary": summary_text[:150] + "..." if len(summary_text) > 150 else summary_text,
                "show_summary": include_summary,
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
    except Exception as e:
        print(f"???砍? {category_name} ??撣? {e}")
        return []


def fetch_university_announcements(url, category_name, scraper_config=None):
    if not scraper_config:
        scraper_config = {
            "article": "#blog-entries article",
            "title_link": ".blog-entry-title.entry-title a",
            "date": ".meta-date"
        }

    if scraper_config.get("parser") == "json_events":
        return fetch_json_announcements(url, category_name, scraper_config)
    if scraper_config.get("parser") == "wordpress_rest":
        return fetch_wordpress_rest_announcements(url, category_name, scraper_config)
    if scraper_config.get("parser") == "oia_next_data":
        return fetch_oia_next_data_announcements(url, category_name, scraper_config)
    if scraper_config.get("parser") == "eshc_table":
        return fetch_eshc_announcements(url, category_name, scraper_config)
    if scraper_config.get("parser") == "table_row":
        return fetch_table_row_announcements(url, category_name, scraper_config)

    try:
        response = create_request_session(url).get(url, headers=REQUEST_HEADERS, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"⚠️ 無法讀取 {category_name}: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        all_news = []
        recent_news = []
        cutoff_date = datetime.now() - timedelta(days=10) # 擴大緩衝到10天
        old_articles_count = 0

        articles = soup.select(scraper_config.get("article", "#blog-entries article"))
        pinned_selector = scraper_config.get("pinned")
        include_summary = scraper_config.get("include_summary", False)
        date_label = scraper_config.get("date_label", "發布日期")
        seen_urls = set()
        
        for article in articles:
            title_selector = scraper_config.get("title")
            title_tag = article.select_one(title_selector) if title_selector else None
            date_tag = article.select_one(scraper_config.get("date", ".meta-date"))
            if title_tag and scraper_config.get("title_remove"):
                for node in title_tag.select(scraper_config.get("title_remove")):
                    node.extract()
            link_selector = scraper_config.get("title_link", ".blog-entry-title.entry-title a")
            link_tag = article.select_one(link_selector)
            if (not link_tag or not link_tag.get("href")) and article.name == "a" and article.get("href"):
                link_tag = article
            if (
                (not link_tag or not link_tag.get("href"))
                and scraper_config.get("parser") == "rcemi_article_box"
            ):
                parent_link = article.find_parent("a", href=True)
                if parent_link:
                    link_tag = parent_link
            
            if link_tag and link_tag.get('href'):
                link_text = normalize_whitespace((title_tag or link_tag).get_text(" ", strip=True))
                if not link_text:
                    continue
                strip_title_suffix = scraper_config.get("strip_title_suffix")
                if strip_title_suffix and link_text.endswith(strip_title_suffix):
                    link_text = link_text[: -len(strip_title_suffix)].rstrip(" .")

                absolute_url = urljoin(url, link_tag.get('href'))
                if absolute_url in seen_urls:
                    continue
                seen_urls.add(absolute_url)

                if scraper_config.get("parser") == "dated_link_list":
                    date_text, title_text = parse_dated_link_text(link_text)
                    summary_text = title_text
                elif scraper_config.get("parser") == "spaced_date_link":
                    date_text, title_text = parse_spaced_date_link_text(link_text)
                    if date_text == "未知日期" or not title_text:
                        continue
                    summary_text = ""
                elif scraper_config.get("parser") == "mgt_card":
                    date_text, title_text = parse_mgt_card_article(article, link_text)
                    if date_text == "未知日期" or not title_text:
                        continue
                    summary_text = ""
                elif scraper_config.get("parser") == "row_date_link":
                    date_text, summary_text = parse_leading_date(article.get_text(" ", strip=True))
                    title_text = link_text
                elif scraper_config.get("parser") == "link_date_text":
                    date_text, title_text = parse_link_leading_date(link_text)
                    summary_text = title_text
                elif scraper_config.get("parser") == "alumni_card":
                    title_tag = article.select_one(scraper_config.get("title", ".title"))
                    summary_tag = article.select_one(scraper_config.get("summary", ".font_con"))
                    date_tag = article.select_one(scraper_config.get("date", ".square_date"))
                    title_text = title_tag.get_text(" ", strip=True) if title_tag else link_text
                    summary_text = summary_tag.get_text(" ", strip=True) if summary_tag else title_text
                    date_text = parse_alumni_date(date_tag.get_text(" ", strip=True) if date_tag else "")
                elif scraper_config.get("parser") == "split_date_card":
                    yearmonth_tag = article.select_one(scraper_config.get("date_yearmonth", ".yearmonth"))
                    day_tag = article.select_one(scraper_config.get("date_day", ".day"))
                    title_text = link_text
                    summary_text = ""
                    date_text = parse_split_date(
                        yearmonth_tag.get_text(" ", strip=True) if yearmonth_tag else "",
                        day_tag.get_text(" ", strip=True) if day_tag else "",
                    )
                elif scraper_config.get("parser") == "ctld_media":
                    title_tag = article.select_one(scraper_config.get("title", "h4.media-heading"))
                    title_text = title_tag.get_text(" ", strip=True) if title_tag else link_text
                    raw_date_text = date_tag.get_text(" ", strip=True) if date_tag else ""
                    date_text, _ = parse_taiwan_date(raw_date_text)
                    summary_text = ""
                elif scraper_config.get("parser") == "cal_news_card":
                    title_text = link_text or link_tag.get("title", "").strip()
                    date_text = parse_cal_date(date_tag)
                    summary_tag = article.select_one(scraper_config.get("summary", ".article"))
                    summary_text = summary_tag.get_text(" ", strip=True) if summary_tag else ""
                elif scraper_config.get("parser") == "rcemi_article_box":
                    date_text, title_text, summary_text = parse_rcemi_article(article, link_text)
                    if date_text == "未知日期" or not title_text:
                        continue
                elif scraper_config.get("parser") == "sdgs_elementskit_card":
                    date_text, title_text, summary_text = parse_sdgs_card_article(article, link_text)
                    if date_text == "?芰?交?" or not title_text:
                        continue
                elif scraper_config.get("parser") == "wix_blog_card":
                    title_tag = article.select_one(scraper_config.get("title", "[data-hook='post-title']"))
                    title_text = normalize_whitespace(
                        title_tag.get_text(" ", strip=True) if title_tag else link_text
                    )
                    raw_date_text = date_tag.get_text(" ", strip=True) if date_tag else ""
                    date_text = parse_yearless_month_day(raw_date_text)
                    summary_tag = article.select_one(scraper_config.get("summary", "[data-hook='post-description']"))
                    summary_text = summary_tag.get_text(" ", strip=True) if summary_tag else ""
                else:
                    raw_date_text = date_tag.get_text(strip=True) if date_tag else ""

                    # 智慧日期解析，分離出乾淨的日期與摘要
                    date_text, summary_text = parse_taiwan_date(raw_date_text)
                    title_text = link_text

                is_pinned = bool(
                    pinned_selector
                    and (
                        article_matches_selector(article, pinned_selector)
                        or article.select_one(pinned_selector)
                    )
                )
                pinned_text_selector = scraper_config.get("pinned_text_selector")
                pinned_text = scraper_config.get("pinned_text")
                if pinned_text_selector and pinned_text:
                    pinned_text_tag = article.select_one(pinned_text_selector)
                    is_pinned = is_pinned or (
                        pinned_text_tag
                        and normalize_whitespace(pinned_text_tag.get_text(" ", strip=True)) == pinned_text
                    )
                if date_text == "未知日期":
                    date_text = parse_date_from_url(absolute_url)

                is_recent = False
                date_is_known = date_text != "未知日期"

                if date_is_known:
                    try:
                        article_date = datetime.strptime(date_text, "%Y-%m-%d")
                        is_recent = article_date >= cutoff_date
                    except ValueError:
                        date_is_known = False

                # Some sites keep "important" pinned rows above newer normal rows.
                # Old pinned rows should not affect preview fallback or old-row cutoff.
                if is_pinned and not is_recent:
                    continue
                
                news_item = {
                    "title": title_text,
                    "url": absolute_url,
                    "date": date_text,
                    "date_label": date_label,
                    "summary": summary_text[:150] + "..." if len(summary_text) > 150 else summary_text,
                    "show_summary": include_summary,
                    "category": category_name
                }
                all_news.append(news_item)
                
                # 📝 修正時間截斷邏輯：確保不被 ValueError 意外重置
                if is_recent:
                    recent_news.append(news_item)
                    old_articles_count = 0 # 真正的新公告，重置計數器
                else:
                    old_articles_count += 1
                    # 🎯 超過 5 天的舊公告，且連續遇到 5 篇，且總數已經夠多，就安全中斷
                    if date_is_known and len(all_news) >= 10 and old_articles_count >= 5:
                        break
        
        # 🎯 確保 main.py 和 JSON 檔案拿到完全一致的前 5 筆 Fallback 資料
        return all_news[:5] if len(recent_news) < 5 else recent_news
        
    except Exception as e:
        print(f"❌ 爬取 {category_name} 時發生異常: {e}")
        return []

if __name__ == "__main__":
    # 測試用
    test_url = "https://www.csie.ntnu.edu.tw/index.php/category/news/announcement/"
    print(fetch_university_announcements(test_url, "資工系辦測試"))
