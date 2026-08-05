import ssl
from urllib.parse import urlparse

import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.exceptions import InsecureRequestWarning
from urllib3.util.retry import Retry


REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
}

urllib3.disable_warnings(InsecureRequestWarning)

RETRY_POLICY = Retry(
    total=1,
    connect=0,
    read=1,
    status=1,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
)


class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = ssl.create_default_context()
        context.set_ciphers("DEFAULT@SECLEVEL=1")
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)


def build_request_options(scraper_config=None):
    options = {
        "headers": REQUEST_HEADERS,
        "timeout": scraper_config.get("timeout", 10) if scraper_config else 10,
    }
    if scraper_config and scraper_config.get("verify_ssl") is False:
        options["verify"] = False
    return options


def create_request_session(url):
    session = requests.Session()
    if urlparse(url).netloc.lower() == "pr.ntnu.edu.tw":
        session.mount(
            "https://pr.ntnu.edu.tw",
            LegacySSLAdapter(max_retries=RETRY_POLICY),
        )
    else:
        adapter = HTTPAdapter(max_retries=RETRY_POLICY)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
    return session
