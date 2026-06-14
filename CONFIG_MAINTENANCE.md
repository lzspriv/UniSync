# UniSync 設定維護指南

`config/university-config.json` 目前仍是支援單位、公告分類、公告網址、爬蟲 selector，以及前端選單結構的主要資料來源。

這份專案暫時不把爬蟲來源搬到 SQL。原因是這些設定比較像「版本化的爬蟲規則」，需要透過 Git commit、review、validation 來追蹤變更；Supabase 比較適合放公告資料、訂閱資料與通知紀錄。

## Selector Presets

當某個公告分類使用常見爬蟲結構時，請優先使用 `selectorPreset`，不要重複貼整組 `selectors`。

範例：

```json
{
  "label": "最新消息",
  "owner": "範例單位",
  "url": "https://example.ntnu.edu.tw/news/",
  "selectorPreset": "wordpress_broad"
}
```

如果某個網站大致符合 preset，但只有少數欄位需要調整，可以同時保留 `selectorPreset` 並加入少量 `selectors` override：

```json
{
  "label": "最新消息",
  "owner": "範例單位",
  "url": "https://example.ntnu.edu.tw/news/",
  "selectorPreset": "wordpress_broad",
  "selectors": {
    "pinned": ".is-sticky"
  }
}
```

Python 的 config loader 會在爬蟲前自動展開 preset，所以 `src/main.py` 和 debug 工具拿到的仍然會是完整 `selectors` 物件。

## Inline Selectors

只有在網站結構很特殊、沒有和其他分類共用時，才直接寫 inline `selectors`。

如果同一組 inline selector 出現在三個以上分類，建議提升成 `selectorPresets`，降低後續維護成本。

## 設定驗證

每次修改 `config/university-config.json` 後，commit 前請先執行：

```powershell
C:\Users\lzspr\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe scripts\validate_config.py
```

驗證器會檢查：

- `selectorPreset` 是否存在
- category 是否缺少 `url`、`label`、`owner`
- schema 選單裡的 `value` 是否都有對應 category
- 每個 category 是否都有 `category-previews.json` 預覽項目
- 預覽項目是否包含 `announcements` 清單
- config 或 preview 檔案是否混入 `????` 亂碼標記

GitHub Actions 在執行爬蟲前也會先跑這個驗證。

## 預覽快取

`category-previews.json` 是產生出來的快取檔，不建議手動編輯。

如果只是調整 config 結構，請避免把無關的 `category-previews.json` 大量 diff 混進同一個 commit。若真的需要更新預覽，請透過爬蟲流程或針對特定分類的預覽產生腳本來更新。

## 建議維護流程

1. 新增或調整分類時，先找是否已有合適的 `selectorPreset`。
2. 若沒有合適 preset，再寫 inline `selectors`。
3. 跑 `scripts\validate_config.py`。
4. 必要時重建相關分類的 preview。
5. 分開 commit：設定結構、預覽快取、UI 或 scraper 行為盡量不要混在同一個 commit。

## Supabase 欄位維護

Telegram 通知會使用 `profiles` 表的兩個欄位。首次部署此功能前，請在 Supabase SQL Editor 執行：

```sql
ALTER TABLE public.profiles
    ADD COLUMN IF NOT EXISTS telegram_bot_token text,
    ADD COLUMN IF NOT EXISTS telegram_chat_id text;
```

`telegram_bot_token` 與 `telegram_chat_id` 都有值時，後端才會送出 Telegram 通知。未填 Telegram 的使用者會維持原本 Discord 通知流程。
