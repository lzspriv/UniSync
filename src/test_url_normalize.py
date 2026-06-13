from announcement_identity import normalize_announcement_url


URLS = [
    "https://pr.ntnu.edu.tw/ntnunews/index.php?mode=data&id=24444",
    "https://pr.ntnu.edu.tw/ntnunews/index.php?mode=data&id=24436",
    "https://pr.ntnu.edu.tw/ntnunews/index.php?mode=data&id=24417",
    "https://pr.ntnu.edu.tw/ntnunews/index.php?mode=data&id=24351",
    "https://pr.ntnu.edu.tw/ntnunews/index.php?mode=data&id=24318",
]


def main():
    normalized_urls = {normalize_announcement_url(url) for url in URLS}

    for index, url in enumerate(URLS, 1):
        print(f"{index}. raw: {url}")
        print(f"   normalized: {normalize_announcement_url(url)}")

    print(f"unique normalized URL count: {len(normalized_urls)}")


if __name__ == "__main__":
    main()
