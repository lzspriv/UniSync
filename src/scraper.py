from scrapers.html_cards import fetch_html_announcements
from scrapers.registry import get_scraper


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
