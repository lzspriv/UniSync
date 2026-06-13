import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
from urllib.parse import urljoin

def parse_taiwan_date(text):
    """
    智慧解析字串中的日期（支援民國、西元格式）。
    成功則回傳 "YYYY-MM-DD"，失敗回傳 "未知日期"。
    """
    if not text:
        return "未知日期", text
        
    # 🔍 尋找民國格式，例如: 115年4月29日 或 114年12月15日
    tw_match = re.search(r'(\d{2,3})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', text)
    if tw_match:
        year = int(tw_match.group(1)) + 1911  # 轉為西元年
        month = int(tw_match.group(2))
        day = int(tw_match.group(3))
        # 將原本文字中的日期標籤部分拿掉，保留純內文當摘要
        summary = text.replace(tw_match.group(0), "").replace("🏷️", "").strip()
        return f"{year}-{month:02d}-{day:02d}", summary

    # 🔍 尋找西元格式，例如: 2026-04-30
    en_match = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', text)
    if en_match:
        summary = text.replace(en_match.group(0), "").strip()
        return f"{en_match.group(1)}-{int(en_match.group(2)):02d}-{int(en_match.group(3)):02d}", summary

    return "未知日期", text

def fetch_university_announcements(url, category_name, scraper_config=None):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    if not scraper_config:
        scraper_config = {
            "article": "#blog-entries article",
            "title_link": ".blog-entry-title.entry-title a",
            "date": ".meta-date"
        }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"⚠️ 無法讀取 {category_name}: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        all_news = []
        recent_news = []
        cutoff_date = datetime.now() - timedelta(days=10) # 擴大緩衝到10天
        old_articles_count = 0

        articles = soup.select(scraper_config.get("article", "#blog-entries article"))
        pinned_selector = scraper_config.get("pinned")
        
        for article in articles:
            link_tag = article.select_one(scraper_config.get("title_link", ".blog-entry-title.entry-title a"))
            date_tag = article.select_one(scraper_config.get("date", ".meta-date"))
            
            if link_tag and link_tag.get('href'):
                raw_date_text = date_tag.get_text(strip=True) if date_tag else ""
                
                # 智慧日期解析，分離出乾淨的日期與摘要
                date_text, summary_text = parse_taiwan_date(raw_date_text)

                is_pinned = bool(pinned_selector and article.select_one(pinned_selector))
                is_recent = False
                date_is_known = date_text != "未知日期"

                if date_is_known:
                    try:
                        article_date = datetime.strptime(date_text, "%Y-%m-%d")
                        is_recent = article_date >= cutoff_date
                    except ValueError:
                        date_is_known = False

                # Some sites keep "important" pinned rows above newer normal rows.
                # Old pinned rows should not affect preview fallback or old-row cutoff.
                if is_pinned and not is_recent:
                    continue
                
                news_item = {
                    "title": link_tag.get_text(strip=True),
                    "url": urljoin(url, link_tag.get('href')),
                    "date": date_text,
                    "summary": summary_text[:150] + "..." if len(summary_text) > 150 else summary_text,
                    "category": category_name
                }
                all_news.append(news_item)
                
                # 📝 修正時間截斷邏輯：確保不被 ValueError 意外重置
                if is_recent:
                    recent_news.append(news_item)
                    old_articles_count = 0 # 真正的新公告，重置計數器
                else:
                    old_articles_count += 1
                    # 🎯 超過 5 天的舊公告，且連續遇到 5 篇，且總數已經夠多，就安全中斷
                    if date_is_known and len(all_news) >= 10 and old_articles_count >= 5:
                        break
        
        # 🎯 確保 main.py 和 JSON 檔案拿到完全一致的前 5 筆 Fallback 資料
        return all_news[:5] if len(recent_news) < 5 else recent_news
        
    except Exception as e:
        print(f"❌ 爬取 {category_name} 時發生異常: {e}")
        return []

if __name__ == "__main__":
    # 測試用
    test_url = "https://www.csie.ntnu.edu.tw/index.php/category/news/announcement/"
    print(fetch_university_announcements(test_url, "資工系辦測試"))
