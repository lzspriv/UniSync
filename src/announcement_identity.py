from urllib.parse import urlsplit, urlunsplit


GISMEE_HOSTS = {"www.gismee.ntnu.edu.tw", "gismee.ntnu.edu.tw"}


def normalize_gismee_announcement_path(path: str):
    normalized_path = path.rstrip("/") or "/"
    segments = [segment for segment in normalized_path.split("/") if segment]

    if len(segments) == 3 and segments[0] == "zh_tw" and segments[1] in ("news", "menu2_1"):
        return f"/zh_tw/news/{segments[2]}"

    if (
        len(segments) == 4
        and segments[0] == "zh_tw"
        and segments[1] == "news"
        and segments[2] == "menu2_2"
    ):
        return f"/zh_tw/news/{segments[3]}"

    return normalized_path


def normalize_announcement_url(raw_url: str):
    """
    Normalize announcement URLs for duplicate detection while preserving query
    strings that may contain a real announcement id.
    """
    if not raw_url:
        return ""

    parsed = urlsplit(raw_url.strip())
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    if not path:
        path = "/"

    if netloc in GISMEE_HOSTS:
        netloc = "www.gismee.ntnu.edu.tw"
        path = normalize_gismee_announcement_path(path)

    return urlunsplit((parsed.scheme.lower(), netloc, path, parsed.query, ""))


def build_announcement_url_candidates(raw_url: str):
    normalized_url = normalize_announcement_url(raw_url)
    if not normalized_url:
        return []

    candidates = []

    def add_candidate(candidate):
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    add_candidate(raw_url)
    add_candidate(normalized_url)

    parsed = urlsplit(normalized_url)
    if parsed.netloc.lower() == "www.gismee.ntnu.edu.tw":
        path = parsed.path.rstrip("/") or "/"
        segments = [segment for segment in path.split("/") if segment]
        if len(segments) == 3 and segments[0] == "zh_tw" and segments[1] == "news":
            slug = segments[2]
            for alias_path in (
                f"/zh_tw/news/{slug}",
                f"/zh_tw/menu2_1/{slug}",
                f"/zh_tw/news/menu2_2/{slug}",
            ):
                add_candidate(urlunsplit((parsed.scheme, parsed.netloc, alias_path, parsed.query, "")))

    return candidates
