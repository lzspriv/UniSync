from urllib.parse import urlsplit, urlunsplit

def normalize_announcement_url(raw_url: str):
    """
    將公告 URL 正規化，避免尾斜線、query string 或 fragment 造成重複判定。
    """
    if not raw_url:
        return ""

    parsed = urlsplit(raw_url.strip())
    path = parsed.path.rstrip("/")
    if not path:
        path = "/"

    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, "", ""))

# 測試 chem_cnews 的 5 個 URL
urls = [
    "https://pr.ntnu.edu.tw/ntnunews/index.php?mode=data&id=24444",
    "https://pr.ntnu.edu.tw/ntnunews/index.php?mode=data&id=24436",
    "https://pr.ntnu.edu.tw/ntnunews/index.php?mode=data&id=24417",
    "https://pr.ntnu.edu.tw/ntnunews/index.php?mode=data&id=24351",
    "https://pr.ntnu.edu.tw/ntnunews/index.php?mode=data&id=24318"
]

print("URL 正規化測試：")
print("-" * 100)
normalized_urls = set()
for i, url in enumerate(urls, 1):
    norm_url = normalize_announcement_url(url)
    normalized_urls.add(norm_url)
    print(f"{i}. 原始：{url}")
    print(f"   正規化後：{norm_url}")
    print()

print(f"✅ 唯一的正規化 URL 數量：{len(normalized_urls)}")
