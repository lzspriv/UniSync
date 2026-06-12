from urllib.parse import urlsplit, urlunsplit

def normalize_announcement_url(raw_url: str):
    """
    將公告 URL 正規化，避免尾斜線或 fragment 造成重複判定。
    保留 query string，因為它通常包含區分公告的唯一標識符（如 id）。
    """
    if not raw_url:
        return ""

    parsed = urlsplit(raw_url.strip())
    path = parsed.path.rstrip("/")
    if not path:
        path = "/"
    
    # 保留 query string 以正確區分有相同路徑但不同 ID 的公告
    query = parsed.query

    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, query, ""))

# 測試新的正規化邏輯
urls = [
    "https://pr.ntnu.edu.tw/ntnunews/index.php?mode=data&id=24444",
    "https://pr.ntnu.edu.tw/ntnunews/index.php?mode=data&id=24436",
    "https://pr.ntnu.edu.tw/ntnunews/index.php?mode=data&id=24417",
]

print("修改後的 URL 正規化測試：")
print("-" * 100)
normalized_urls = set()
for i, url in enumerate(urls, 1):
    norm_url = normalize_announcement_url(url)
    normalized_urls.add(norm_url)
    print(f"{i}. 原始：{url}")
    print(f"   正規化後：{norm_url}")
    print()

print(f"✅ 唯一的正規化 URL 數量：{len(normalized_urls)}")
print("\n✨ 修改成功！現在每個公告都會被正確區分。")
