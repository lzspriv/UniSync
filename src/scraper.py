import requests
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import ssl
from urllib.parse import urljoin, urlparse


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
        
    # 🔍 尋找民國格式，例如: 115年4月29日 或 114年12月15日
    tw_match = re.search(r'(\d{2,3})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', text)
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

    match = re.match(r"^\s*(\d{4})[-/](\d{1,2})[-/](\d{1,2})", text)
    if match:
        year, month, day = match.groups()
        summary = text[match.end():].lstrip(" |｜-—\t")
        return f"{year}-{int(month):02d}-{int(day):02d}", summary

    return parse_taiwan_date(text)


def parse_split_date(yearmonth_text, day_text):
    match = re.search(r"(\d{4})[-/](\d{1,2})", yearmonth_text or "")
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
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
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


def fetch_university_announcements(url, category_name, scraper_config=None):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    if not scraper_config:
        scraper_config = {
            "article": "#blog-entries article",
            "title_link": ".blog-entry-title.entry-title a",
            "date": ".meta-date"
        }

    if scraper_config.get("parser") == "json_events":
        return fetch_json_announcements(url, category_name, scraper_config)

    try:
        response = create_request_session(url).get(url, headers=headers, timeout=10)
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
        seen_urls = set()
        
        for article in articles:
            link_tag = article.select_one(scraper_config.get("title_link", ".blog-entry-title.entry-title a"))
            date_tag = article.select_one(scraper_config.get("date", ".meta-date"))
            
            if link_tag and link_tag.get('href'):
                link_text = normalize_whitespace(link_tag.get_text(" ", strip=True))
                absolute_url = urljoin(url, link_tag.get('href'))
                if absolute_url in seen_urls:
                    continue
                seen_urls.add(absolute_url)

                if scraper_config.get("parser") == "dated_link_list":
                    date_text, title_text = parse_dated_link_text(link_text)
                    summary_text = title_text
                elif scraper_config.get("parser") == "row_date_link":
                    date_text, summary_text = parse_leading_date(article.get_text(" ", strip=True))
                    title_text = link_text
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
