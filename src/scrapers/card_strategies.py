import re
from datetime import datetime

from scraper_parsing import (
    normalize_whitespace,
    parse_alumni_date,
    parse_cal_date,
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


def parse_default(article, link_text, date_tag, scraper_config):
    raw_date_text = date_tag.get_text(strip=True) if date_tag else ""
    date_text, summary_text = parse_taiwan_date(raw_date_text)
    return date_text, link_text, summary_text


def parse_dated_link(_article, link_text, _date_tag, _scraper_config):
    date_text, title_text = parse_dated_link_text(link_text)
    return date_text, title_text, title_text


def parse_spaced_date_link(_article, link_text, _date_tag, _scraper_config):
    date_text, title_text = parse_spaced_date_link_text(link_text)
    if date_text == "未知日期" or not title_text:
        return None
    return date_text, title_text, ""


def parse_management_card(article, link_text, _date_tag, _scraper_config):
    date_text, title_text = parse_mgt_card_article(article, link_text)
    if date_text == "未知日期" or not title_text:
        return None
    return date_text, title_text, ""


def parse_row_date_link(article, link_text, _date_tag, _scraper_config):
    date_text, summary_text = parse_leading_date(article.get_text(" ", strip=True))
    return date_text, link_text, summary_text


def parse_link_date_text(_article, link_text, _date_tag, _scraper_config):
    date_text, title_text = parse_link_leading_date(link_text)
    return date_text, title_text, title_text


def parse_alumni_card(article, link_text, _date_tag, scraper_config):
    title_tag = article.select_one(scraper_config.get("title", ".title"))
    summary_tag = article.select_one(scraper_config.get("summary", ".font_con"))
    card_date_tag = article.select_one(scraper_config.get("date", ".square_date"))
    title_text = title_tag.get_text(" ", strip=True) if title_tag else link_text
    summary_text = summary_tag.get_text(" ", strip=True) if summary_tag else title_text
    date_text = parse_alumni_date(card_date_tag.get_text(" ", strip=True) if card_date_tag else "")
    return date_text, title_text, summary_text


def parse_split_date_card(article, link_text, _date_tag, scraper_config):
    yearmonth_tag = article.select_one(scraper_config.get("date_yearmonth", ".yearmonth"))
    day_tag = article.select_one(scraper_config.get("date_day", ".day"))
    date_text = parse_split_date(
        yearmonth_tag.get_text(" ", strip=True) if yearmonth_tag else "",
        day_tag.get_text(" ", strip=True) if day_tag else "",
    )
    return date_text, link_text, ""


def parse_ctld_media(article, link_text, date_tag, scraper_config):
    title_tag = article.select_one(scraper_config.get("title", "h4.media-heading"))
    title_text = title_tag.get_text(" ", strip=True) if title_tag else link_text
    raw_date_text = date_tag.get_text(" ", strip=True) if date_tag else ""
    date_text, _ = parse_taiwan_date(raw_date_text)
    return date_text, title_text, ""


def parse_cal_news_card(article, link_text, date_tag, scraper_config):
    date_text = parse_cal_date(date_tag)
    summary_tag = article.select_one(scraper_config.get("summary", ".article"))
    summary_text = summary_tag.get_text(" ", strip=True) if summary_tag else ""
    return date_text, link_text, summary_text


def parse_rcemi_card(article, link_text, _date_tag, _scraper_config):
    date_text, title_text, summary_text = parse_rcemi_article(article, link_text)
    if date_text == "未知日期" or not title_text:
        return None
    return date_text, title_text, summary_text


def parse_sdgs_card(article, link_text, _date_tag, _scraper_config):
    date_text, title_text, summary_text = parse_sdgs_card_article(article, link_text)
    if not title_text:
        return None
    return date_text, title_text, summary_text


def parse_wix_blog_card(article, link_text, date_tag, scraper_config):
    title_tag = article.select_one(scraper_config.get("title", "[data-hook='post-title']"))
    title_text = normalize_whitespace(
        title_tag.get_text(" ", strip=True) if title_tag else link_text
    )
    raw_date_text = date_tag.get_text(" ", strip=True) if date_tag else ""
    date_text = parse_yearless_month_day(raw_date_text)
    summary_tag = article.select_one(scraper_config.get("summary", "[data-hook='post-description']"))
    summary_text = summary_tag.get_text(" ", strip=True) if summary_tag else ""
    return date_text, title_text, summary_text


def parse_shopify_blog_card(article, link_text, date_tag, scraper_config):
    raw_date_text = ""
    if date_tag:
        raw_date_text = date_tag.get("datetime") or date_tag.get_text(" ", strip=True)
    date_text, _ = parse_taiwan_date(raw_date_text)
    summary_tag = article.select_one(scraper_config.get("summary", ".blog-post-card__content-text"))
    summary_text = summary_tag.get_text(" ", strip=True) if summary_tag else ""
    return date_text, link_text, summary_text


CARD_STRATEGIES = {
    "dated_link_list": parse_dated_link,
    "spaced_date_link": parse_spaced_date_link,
    "mgt_card": parse_management_card,
    "row_date_link": parse_row_date_link,
    "link_date_text": parse_link_date_text,
    "alumni_card": parse_alumni_card,
    "split_date_card": parse_split_date_card,
    "ctld_media": parse_ctld_media,
    "cal_news_card": parse_cal_news_card,
    "rcemi_article_box": parse_rcemi_card,
    "sdgs_elementskit_card": parse_sdgs_card,
    "wix_blog_card": parse_wix_blog_card,
    "shopify_blog_card": parse_shopify_blog_card,
}


def parse_article_content(parser_name, article, link_text, date_tag, scraper_config):
    strategy = CARD_STRATEGIES.get(parser_name, parse_default)
    return strategy(article, link_text, date_tag, scraper_config)
