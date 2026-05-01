import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def fetch_ntnu_csie_category(url, category_name):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"⚠️ 無法讀取 {category_name}: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        all_news = []  # 所有爬到的公告（不限時間）
        recent_news = []  # 最近 5 天內的公告
        cutoff_date = datetime.now() - timedelta(days=5)  # 最近 5 天的截止日期
        old_articles_count = 0  # 連續超過 5 天的公告計數器

        # 定位所有文章區塊
        articles = soup.select('#blog-entries article')
        
        for article in articles:
            link_tag = article.select_one('.blog-entry-title.entry-title a')
            # 🔍 定位日期標籤
            date_tag = article.select_one('.meta-date')
            
            if link_tag:
                # 清理日期字串，去掉多餘的標籤文字
                date_text = date_tag.get_text(strip=True).replace("Post published:", "") if date_tag else "未知日期"
                
                news_item = {
                    "title": link_tag.get_text(strip=True),
                    "url": link_tag.get('href'),
                    "date": date_text,
                    "category": category_name
                }
                
                # 先加入 all_news（用於備援）
                all_news.append(news_item)
                
                # 判斷是否在 5 天內
                try:
                    article_date = datetime.strptime(date_text, "%Y-%m-%d")
                    if article_date >= cutoff_date:
                        recent_news.append(news_item)
                        old_articles_count = 0  # 重置計數器
                    else:
                        old_articles_count += 1
                        # 🎯 提前停止：已爬 20 篇且連續遇到 5 篇舊公告，就停止
                        if len(all_news) >= 20 and old_articles_count >= 5:
                            break
                except ValueError:
                    # 無法解析日期，當作新公告處理
                    recent_news.append(news_item)
                    old_articles_count = 0
        
        # 🎯 智慧邏輯：5 天內不足 5 篇就爬 5 篇；5 天內滿 5 篇以上就只爬 5 天內的
        if len(recent_news) < 5:
            # 5 天內不足 5 篇，取前 5 篇（可能跨越時間）
            news_list = all_news[:5]
        else:
            # 5 天內滿 5 篇以上，只保留 5 天內的（會自動被截斷為預覽用）
            news_list = recent_news
        
        return news_list
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        return []

if __name__ == "__main__":
    test_url = "https://www.csie.ntnu.edu.tw/index.php/category/news/announcement/"
    print(f"🔍 正在測試抓取：{test_url}...")
    results = fetch_ntnu_csie_category(test_url, "系所公告")
    
    if not results:
        print("查無資料")
    else:
        print(f"✅ 成功抓取 {len(results)} 筆資料，第一筆日期：{results[0]['date']}")