import os
from dotenv import load_dotenv
from supabase import create_client

# 載入環境變數
load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

def test_connection():
    try:
        # 嘗試從 announcements 表抓取一筆資料（即便現在是空的）
        response = supabase.table("announcements").select("*").limit(1).execute()
        print("✅ 連線成功！")
        print("目前資料庫內容：", response.data)
    except Exception as e:
        print("❌ 連線失敗，請檢查 URL 或 Key 是否正確")
        print(f"錯誤訊息: {e}")

if __name__ == "__main__":
    test_connection()