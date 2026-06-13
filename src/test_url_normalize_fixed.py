from announcement_identity import build_announcement_url_candidates, normalize_announcement_url


GISMEE_URLS = [
    "https://www.gismee.ntnu.edu.tw/zh_tw/news/%E6%9C%AC%E6%A0%A1115%E5%AD%B8%E5%B9%B4%E5%BA%A6%E5%8D%9A%E5%A3%AB%E7%8F%AD%E8%80%83%E8%A9%A6%E5%85%A5%E5%AD%B8%E9%8C%84%E5%8F%96%E5%90%8D%E5%96%AE-82555820",
    "https://www.gismee.ntnu.edu.tw/zh_tw/menu2_1/%E6%9C%AC%E6%A0%A1115%E5%AD%B8%E5%B9%B4%E5%BA%A6%E5%8D%9A%E5%A3%AB%E7%8F%AD%E8%80%83%E8%A9%A6%E5%85%A5%E5%AD%B8%E9%8C%84%E5%8F%96%E5%90%8D%E5%96%AE-82555820",
]


def main():
    normalized_urls = {normalize_announcement_url(url) for url in GISMEE_URLS}

    for index, url in enumerate(GISMEE_URLS, 1):
        print(f"{index}. raw: {url}")
        print(f"   normalized: {normalize_announcement_url(url)}")

    candidates = build_announcement_url_candidates(GISMEE_URLS[0])
    print(f"unique normalized URL count: {len(normalized_urls)}")
    print(f"candidate count: {len(candidates)}")

    assert len(normalized_urls) == 1
    assert all(url in candidates for url in GISMEE_URLS)


if __name__ == "__main__":
    main()
