import requests
from bs4 import BeautifulSoup

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
        news_list = []

        # 定位所有文章區塊
        articles = soup.select('#blog-entries article')
        
        for article in articles:
            link_tag = article.select_one('.blog-entry-title.entry-title a')
            # 🔍 新增：定位日期標籤
            date_tag = article.select_one('.meta-date')
            
            if link_tag:
                # 清理日期字串，去掉多餘的標籤文字
                date_text = date_tag.get_text(strip=True).replace("Post published:", "") if date_tag else "未知日期"
                
                news_list.append({
                    "title": link_tag.get_text(strip=True),
                    "url": link_tag.get('href'),
                    "date": date_text, # ✅ 現在有 date 這個 Key 了！
                    "category": category_name
                })
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