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

TLS12_ONLY_HOSTS = {
    "www.hakka.ntnu.edu.tw",
    "www.iaao.ntnu.edu.tw",
    "www.ohsp.ntnu.edu.tw",
}


class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = ssl.create_default_context()
        context.set_ciphers("DEFAULT@SECLEVEL=1")
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)


class TLS12Adapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.maximum_version = ssl.TLSVersion.TLSv1_2
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)


class FingerprintSSLAdapter(HTTPAdapter):
    def __init__(self, certificate_sha256, *args, **kwargs):
        self.certificate_sha256 = certificate_sha256
        super().__init__(*args, **kwargs)

    def cert_verify(self, conn, url, verify, cert):
        super().cert_verify(conn, url, False, cert)
        conn.assert_fingerprint = self.certificate_sha256


class MultiFingerprintSession(requests.Session):
    def __init__(self, origin, certificate_sha256s):
        super().__init__()
        self.origin = origin
        self.certificate_sha256s = list(certificate_sha256s)
        self.preferred_fingerprint_index = 0

    def mount_fingerprint(self, fingerprint):
        previous_adapter = self.adapters.get(self.origin)
        if previous_adapter:
            previous_adapter.close()
        self.mount(
            self.origin,
            FingerprintSSLAdapter(
                fingerprint,
                max_retries=RETRY_POLICY,
            ),
        )

    def request(self, method, url, **kwargs):
        preferred_index = self.preferred_fingerprint_index
        fingerprint_indexes = [preferred_index] + [
            index
            for index in range(len(self.certificate_sha256s))
            if index != preferred_index
        ]
        last_error = None

        for index in fingerprint_indexes:
            self.mount_fingerprint(self.certificate_sha256s[index])
            try:
                response = super().request(method, url, **kwargs)
                self.preferred_fingerprint_index = index
                return response
            except requests.exceptions.SSLError as error:
                last_error = error
                if "Fingerprints did not match" not in str(error):
                    raise

        raise last_error


def normalize_certificate_fingerprints(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [str(fingerprint) for fingerprint in value if fingerprint]
    return []


def build_request_options(scraper_config=None):
    options = {
        "headers": REQUEST_HEADERS,
        "timeout": scraper_config.get("timeout", 10) if scraper_config else 10,
    }
    if scraper_config and scraper_config.get("verify_ssl") is False:
        options["verify"] = False
    return options


def create_request_session(url, scraper_config=None):
    parsed_url = urlparse(url)
    origin = f"{parsed_url.scheme}://{parsed_url.netloc}"
    certificate_sha256s = normalize_certificate_fingerprints(
        (scraper_config or {}).get("tls_certificate_sha256")
    )
    if len(certificate_sha256s) > 1:
        session = MultiFingerprintSession(origin, certificate_sha256s)
        session.mount_fingerprint(certificate_sha256s[0])
    else:
        session = requests.Session()

    if len(certificate_sha256s) == 1:
        session.mount(
            origin,
            FingerprintSSLAdapter(
                certificate_sha256s[0],
                max_retries=RETRY_POLICY,
            ),
        )
    elif not certificate_sha256s and parsed_url.netloc.lower() in TLS12_ONLY_HOSTS:
        session.mount(
            origin,
            TLS12Adapter(max_retries=RETRY_POLICY),
        )
    elif not certificate_sha256s and parsed_url.netloc.lower() == "pr.ntnu.edu.tw":
        session.mount(
            "https://pr.ntnu.edu.tw",
            LegacySSLAdapter(max_retries=RETRY_POLICY),
        )
    elif not certificate_sha256s:
        adapter = HTTPAdapter(max_retries=RETRY_POLICY)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
    return session
