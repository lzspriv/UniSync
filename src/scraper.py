from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
from urllib.parse import quote, urljoin

from scraper_http import (
    REQUEST_HEADERS,
    RETRY_POLICY,
    LegacySSLAdapter,
    build_request_options,
    create_request_session,
)
from scraper_parsing import (
    article_matches_selector,
    extract_onclick_url,
    normalize_whitespace,
    parse_alumni_date,
    parse_cal_date,
    parse_date_from_url,
    parse_dated_link_text,
    parse_leading_date,
    parse_link_leading_date,
    parse_mgt_card_article,
    parse_spaced_date_link_text,
    parse_split_date,
    parse_taiwan_date,
    parse_yearless_month_day,
)
from scrapers.atom_json import fetch_atom_json_announcements
from scrapers.irels_news import fetch_irels_news_announcements
from scrapers.json_events import fetch_json_announcements
from scrapers.oia_next_data import fetch_oia_next_data_announcements
from scrapers.wordpress_rest import fetch_wordpress_rest_announcements


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
        response = create_request_session(url).get(url, **build_request_options(scraper_config))
        response.encoding = "utf-8"

        if response.status_code != 200:
            print(f"⚠️ 無法讀取 {category_name}: {response.status_code}")
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
        date_label = scraper_config.get("date_label", "\u767c\u5e03\u65e5\u671f")

        for article in soup.select(scraper_config.get("article", "tr")):
            title_tag = None
            title_selector = scraper_config.get("title")
            if title_selector:
                title_tag = article.select_one(title_selector)

            link_selector = scraper_config.get("title_link", "a[href]")
            link_tag = article.select_one(link_selector)
            if (not link_tag or not link_tag.get("href")) and article.name == "a" and article.get("href"):
                link_tag = article
            if not title_tag:
                title_tag = link_tag

            title_text = normalize_whitespace(
                title_tag.get_text(" ", strip=True) if title_tag else ""
            )
            if (
                link_tag
                and link_tag.get("title")
                and (scraper_config.get("prefer_title_attr") or title_text.startswith("\u6a19\u984c:"))
            ):
                title_text = normalize_whitespace(link_tag.get("title"))
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
        print(f"❌ 爬取 {category_name} 時發生異常: {e}")
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
    if scraper_config.get("parser") == "atom_json":
        return fetch_atom_json_announcements(url, category_name, scraper_config)
    if scraper_config.get("parser") == "irels_news":
        return fetch_irels_news_announcements(url, category_name, scraper_config)
    if scraper_config.get("parser") == "wordpress_rest":
        return fetch_wordpress_rest_announcements(url, category_name, scraper_config)
    if scraper_config.get("parser") == "oia_next_data":
        return fetch_oia_next_data_announcements(url, category_name, scraper_config)
    if scraper_config.get("parser") == "eshc_table":
        return fetch_eshc_announcements(url, category_name, scraper_config)
    if scraper_config.get("parser") == "table_row":
        return fetch_table_row_announcements(url, category_name, scraper_config)

    try:
        response = create_request_session(url).get(url, **build_request_options(scraper_config))
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
