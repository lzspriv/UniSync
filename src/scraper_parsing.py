import re
from datetime import datetime, timedelta
from html import unescape
from urllib.parse import urlparse

from bs4 import BeautifulSoup


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

    ad_zh_match = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", text)
    if ad_zh_match:
        year, month, day = ad_zh_match.groups()
        summary = text.replace(ad_zh_match.group(0), "").strip()
        return f"{year}-{int(month):02d}-{int(day):02d}", summary

    tw_match = re.search(r"(?<!\d)(\d{2,3})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", text)
    if tw_match:
        year = int(tw_match.group(1)) + 1911
        month = int(tw_match.group(2))
        day = int(tw_match.group(3))
        summary = text.replace(tw_match.group(0), "").replace("🏷️", "").strip()
        return f"{year}-{month:02d}-{day:02d}", summary

    tw_slash_match = re.search(r"(?<!\d)(\d{2,3})[-/.](\d{1,2})[-/.](\d{1,2})(?!\d)", text)
    if tw_slash_match:
        year = int(tw_slash_match.group(1)) + 1911
        month = int(tw_slash_match.group(2))
        day = int(tw_slash_match.group(3))
        summary = text.replace(tw_slash_match.group(0), "").strip()
        return f"{year}-{month:02d}-{day:02d}", summary

    en_match = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", text)
    if en_match:
        summary = text.replace(en_match.group(0), "").strip()
        return f"{en_match.group(1)}-{int(en_match.group(2)):02d}-{int(en_match.group(3)):02d}", summary

    hybrid_match = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", text.replace("/", "-"))
    if hybrid_match:
        summary = text.replace(hybrid_match.group(0), "").strip()
        return (
            f"{hybrid_match.group(1)}-{int(hybrid_match.group(2)):02d}-{int(hybrid_match.group(3)):02d}",
            summary,
        )

    zh_comma_match = re.search(r"(\d{1,2})\s*月\s*(\d{1,2})\s*,\s*((?:19|20)\d{2})", text)
    if zh_comma_match:
        month, day, year = zh_comma_match.groups()
        summary = text.replace(zh_comma_match.group(0), "").strip()
        return f"{year}-{int(month):02d}-{int(day):02d}", summary

    zh_month_match = re.search(r"(\d{4})\s*(?:年)?\s*(\d{1,2})\s*月\s*(\d{1,2})\s*(?:日)?", text)
    if zh_month_match:
        year, month, day = zh_month_match.groups()
        summary = text.replace(zh_month_match.group(0), "").strip()
        return f"{year}-{int(month):02d}-{int(day):02d}", summary

    return "未知日期", text


def normalize_whitespace(text):
    return re.sub(r"\s+", " ", text or "").strip()


def clean_html_text(value):
    text = BeautifulSoup(value or "", "html.parser").get_text(" ", strip=True)
    return normalize_whitespace(unescape(text))


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
        match = re.search(r"(?:^|/)((?:19|20)\d{2})(\d{2})(\d{2})[_-]", parsed_url.path)
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
