# Autoposting-Social-Media-Python
這是一個基於 Python 的自動發文系統，可以自動發布內容到 Facebook 和 Instagram 等社群媒體平台。

## 功能特色
- ✅ 自動發布到 Facebook
- ✅ 自動發布到 Instagram
- ✅ 使用 GPT-4 生成專業醫療相關內容
- ✅ 自動抓取三立新聞網內容
- ✅ 支援手動模式和自動模式
- ✅ 彈性的發文時間設定

## 安裝步驟

### 1. 安裝相依套件
```bash
pip install -r requirements.txt
```

必要套件包含：
- facebook-sdk：Facebook API
- instagrapi：Instagram API
- openai：GPT-4 API
- aiohttp：非同步 HTTP 請求
- beautifulsoup4：網頁解析
- pillow：圖片處理

### 2. 設定配置檔案

在專案根目錄創建 `config.json`：
```json
{
  "API_KEY": "your_openai_api_key",
  "FB_TOKEN": "your_facebook_access_token",
  "IG_USERNAME": "your_instagram_username",
  "IG_PASSWORD": "your_instagram_password",
  "NEWS": "https://www.setn.com/ViewAll.aspx",
  "MODE": "setn",
  "POST_DELAY_MIN": 1800,
  "POST_DELAY_MAX": 7200,
  "POST_TO_FACEBOOK": true,
  "POST_TO_INSTAGRAM": true
}
```

#### 設定說明：
- `API_KEY`：OpenAI API 金鑰
- `FB_TOKEN`：Facebook Graph API 存取權杖
- `IG_USERNAME`：Instagram 帳號
- `IG_PASSWORD`：Instagram 密碼
- `NEWS`：新聞來源網址
- `MODE`：執行模式（setn / text / manual）
- `POST_DELAY_MIN`：最小發文間隔（秒）
- `POST_DELAY_MAX`：最大發文間隔（秒）
- `POST_TO_FACEBOOK`：是否發布到 Facebook
- `POST_TO_INSTAGRAM`：是否發布到 Instagram

### 3. 環境變數（可選）
也可以使用環境變數替代 config.json，在 Railway 或 Heroku 等平台特別有用：
```bash
export API_KEY="your_openai_api_key"
export FB_TOKEN="your_facebook_access_token"
export IG_USERNAME="your_instagram_username"
export IG_PASSWORD="your_instagram_password"
export POST_TO_FACEBOOK="true"
export POST_TO_INSTAGRAM="true"
```

## 使用方式

### 執行程式
```bash
python autopost.py
```

### 三種模式

#### 1. setn 模式（預設）
自動從三立新聞網抓取最新新聞，使用 GPT-4 生成醫療相關評論，並自動發布到 Facebook 和/或 Instagram：
```json
{
  "MODE": "setn"
}
```

#### 2. text 模式
純粹使用 GPT-4 生成內容並自動發布：
```json
{
  "MODE": "text"
}
```

#### 3. manual 模式
手動輸入主題或新聞網址，預覽生成內容後決定是否發布：
```json
{
  "MODE": "manual"
}
```

## Instagram 特色功能
- 自動生成文字圖片（Instagram 需要圖片才能發文）
- 智慧文字換行與排版
- 支援長文本自動縮減

## 注意事項
1. **Facebook Token**：需要從 Facebook Developer 平台取得有效的 Page Access Token
2. **Instagram 登入**：首次登入可能需要驗證，建議先在本地測試
3. **API 額度**：注意 OpenAI API 的使用額度
4. **發文頻率**：建議設定合理的發文間隔，避免被平台限制

## 部署到 Railway/Heroku
1. 將程式碼推送到 Git 儲存庫
2. 在平台設定環境變數
3. 平台會自動使用 `Procfile` 啟動程式

## 授權
此專案僅供學習參考使用。

## 社群媒體連結
- Facebook：https://www.facebook.com/codingrdx/
- Twitter：https://twitter.com/venom_rdx


