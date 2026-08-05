from scraper_http import (
    REQUEST_HEADERS,
    RETRY_POLICY,
    LegacySSLAdapter,
    build_request_options,
    create_request_session,
)
from scraper_parsing import (
    SafeFormatDict,
    article_matches_selector,
    clean_html_text,
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
from scrapers.eshc_table import fetch_eshc_announcements
from scrapers.html_cards import (
    fetch_html_announcements,
    parse_rcemi_article,
    parse_sdgs_card_article,
)
from scrapers.irels_news import fetch_irels_news_announcements
from scrapers.json_events import fetch_json_announcements
from scrapers.oia_next_data import fetch_oia_next_data_announcements
from scrapers.registry import get_scraper
from scrapers.table_row import fetch_table_row_announcements
from scrapers.wordpress_rest import fetch_wordpress_rest_announcements


DEFAULT_SCRAPER_CONFIG = {
    "article": "#blog-entries article",
    "title_link": ".blog-entry-title.entry-title a",
    "date": ".meta-date",
}


def fetch_university_announcements(url, category_name, scraper_config=None):
    resolved_config = scraper_config or DEFAULT_SCRAPER_CONFIG.copy()
    registered_scraper = get_scraper(resolved_config.get("parser"))
    if registered_scraper:
        return registered_scraper(url, category_name, resolved_config)
    return fetch_html_announcements(url, category_name, resolved_config)


if __name__ == "__main__":
    test_url = "https://www.csie.ntnu.edu.tw/index.php/category/news/announcement/"
    print(fetch_university_announcements(test_url, "資工系辦測試"))
