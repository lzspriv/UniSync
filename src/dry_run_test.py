import sys
from pathlib import Path

# 修正：將當前檔案所在的 src 目錄加入 Python 搜尋路徑，徹底解決路徑 import 問題
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

from config_loader import load_category_config
from scraper import fetch_university_announcements

CONFIG_PATH = current_dir.parent / "config" / "university-config.json"

def run_diagnostic():
    print("🧪 開始進行理學院各系所爬蟲相容性診斷...")
    print("=" * 60)
    
    category_urls, category_labels, categories = load_category_config(CONFIG_PATH)
    
    failed_sites = []
    success_count = 0
    
    for cat_id, meta in categories.items():
        url = category_urls.get(cat_id, meta.get("url", ""))
        display_name = category_labels.get(cat_id, cat_id)
        
        # 讀取個別選擇器，如果沒有就傳 None (使用 scraper.py 的預設值)
        selectors = meta.get("selectors", None)
        
        print(f"📡 測試中 -> {display_name}...", end="", flush=True)
        
        # 進行 Dry-run 測試
        results = fetch_university_announcements(url, display_name, selectors)
        
        if not results:
            print(" ❌ [失敗：抓到 0 筆資料]")
            failed_sites.append({
                "id": cat_id,
                "name": display_name,
                "url": url
            })
        else:
            print(f"  [成功：抓到 {len(results)} 筆]")
            success_count += 1

    print("=" * 60)
    print(f"📊 診斷報告結束：成功 {success_count} 個分類，失敗 {len(failed_sites)} 個分類。")
    
    if failed_sites:
        print("\n🚨 以下是抓不到資料的「戰犯清單」，我們需要幫它們客製化 Selector：")
        for idx, site in enumerate(failed_sites, 1):
            print(f"{idx}. [{site['id']}] {site['name']}")
            print(f"   🔗 網址: {site['url']}")
    else:
        print("\n🎉 太完美了！目前所有設定的網頁結構均能 100% 完美相容！")

if __name__ == "__main__":
    run_diagnostic()
