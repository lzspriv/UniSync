from datetime import datetime, timedelta
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup

from scraper_http import build_request_options, create_request_session
from scraper_parsing import (
    article_matches_selector,
    extract_onclick_url,
    normalize_whitespace,
    parse_leading_date,
    parse_taiwan_date,
)


def fetch_table_row_announcements(url, category_name, scraper_config):
    try:
        response = create_request_session(url, scraper_config).get(
            url, **build_request_options(scraper_config)
        )
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
        date_label = scraper_config.get("date_label", "發布日期")

        for article in soup.select(scraper_config.get("article", "tr")):
            date_selector = scraper_config.get("date")
            date_tag = article.select_one(date_selector) if date_selector else None
            title_tag = None
            title_selector = scraper_config.get("title")
            if title_selector:
                title_tag = article.select_one(title_selector)
                if title_tag and scraper_config.get("title_remove"):
                    for node in title_tag.select(scraper_config["title_remove"]):
                        node.extract()

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
                and (scraper_config.get("prefer_title_attr") or title_text.startswith("標題:"))
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
            item_date_label = "置頂公告" if is_pinned else date_label
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
    except Exception as error:
        print(f"❌ 爬取 {category_name} 時發生異常: {error}")
        return []
