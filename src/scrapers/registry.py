from scrapers.atom_json import fetch_atom_json_announcements
from scrapers.eshc_table import fetch_eshc_announcements
from scrapers.irels_news import fetch_irels_news_announcements
from scrapers.json_events import fetch_json_announcements
from scrapers.oia_next_data import fetch_oia_next_data_announcements
from scrapers.oddi_lazy_news import fetch_oddi_lazy_news_announcements
from scrapers.table_row import fetch_table_row_announcements
from scrapers.wordpress_rest import fetch_wordpress_rest_announcements


SCRAPER_REGISTRY = {
    "json_events": fetch_json_announcements,
    "atom_json": fetch_atom_json_announcements,
    "irels_news": fetch_irels_news_announcements,
    "wordpress_rest": fetch_wordpress_rest_announcements,
    "oia_next_data": fetch_oia_next_data_announcements,
    "oddi_lazy_news": fetch_oddi_lazy_news_announcements,
    "eshc_table": fetch_eshc_announcements,
    "table_row": fetch_table_row_announcements,
}


def get_scraper(parser_name):
    return SCRAPER_REGISTRY.get(parser_name)
