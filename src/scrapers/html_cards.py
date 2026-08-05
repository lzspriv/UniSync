import re
from datetime import datetime, timedelta
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scraper_http import build_request_options, create_request_session
from scraper_parsing import (
    article_matches_selector,
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

    date_text = "未知日期"
    date_tag = article.select_one(".elementskit-meta-lists")
    if date_tag:
        date_source = normalize_whitespace(date_tag.get_text(" ", strip=True))
        match = re.search(r"(\d{1,2})\s+(\d{1,2})\s*月", date_source)
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


def fetch_html_announcements(url, category_name, scraper_config):
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

            if link_tag and link_tag.get("href"):
                link_text = normalize_whitespace((title_tag or link_tag).get_text(" ", strip=True))
                if not link_text:
                    continue
                strip_title_suffix = scraper_config.get("strip_title_suffix")
                if strip_title_suffix and link_text.endswith(strip_title_suffix):
                    link_text = link_text[: -len(strip_title_suffix)].rstrip(" .")

                absolute_url = urljoin(url, link_tag.get("href"))
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

                if is_pinned and not is_recent:
                    continue

                news_item = {
                    "title": title_text,
                    "url": absolute_url,
                    "date": date_text,
                    "date_label": date_label,
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
    except Exception as error:
        print(f"❌ 爬取 {category_name} 時發生異常: {error}")
        return []
