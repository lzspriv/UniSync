from datetime import datetime, timedelta
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scraper_http import build_request_options, create_request_session
from scraper_parsing import (
    article_matches_selector,
    normalize_whitespace,
    parse_date_from_url,
)
from scrapers.card_strategies import (
    parse_article_content,
    parse_rcemi_article,
    parse_sdgs_card_article,
)


def fetch_html_announcements(url, category_name, scraper_config):
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

                parsed_content = parse_article_content(
                    scraper_config.get("parser"),
                    article,
                    link_text,
                    date_tag,
                    scraper_config,
                )
                if parsed_content is None:
                    continue
                date_text, title_text, summary_text = parsed_content

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
