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
export IG_SESSIONID="your_verified_sessionid"   # 可選：以已驗證的 sessionid 直接登入
export IG_SETTINGS_PATH="downloads/instagrapi_settings.json"  # 可選：settings 檔案路徑（預設）
export IG_SETTINGS_JSON='{ "some": "json" }'  # 可選：settings JSON 內容（雲端貼上）
export IG_PROXY="http://user:pass@host:port"    # 可選：HTTP/HTTPS 代理
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

### Instagram 在雲端的穩定登入策略
- ✅ **優先使用已驗證的 `IG_SESSIONID`**：在本機完成一次登入與驗證後，擷取 sessionid 並設定到環境變數，雲端可直接使用。
- ✅ **載入既有 settings**：提供 `IG_SETTINGS_JSON`（直接貼 JSON 內容）或 `IG_SETTINGS_PATH`（檔案路徑，預設為 `downloads/instagrapi_settings.json`）。程式啟動時會先載入，並在成功登入後自動 `dump_settings` 以利後續重用。
- ✅ **代理（選用）**：若雲端 IP 經常被挑戰，可設定 `IG_PROXY` 使用固定出口。

> 提示：Railway 的檔案系統可能不是持久化的，若無法保留 settings 檔，建議改用 `IG_SETTINGS_JSON` 直接以環境變數提供設定內容。

### 同步環境變數到 Railway（安全）
- 不要在 GitHub 提交真實機密（`config.json`、`.env`、`downloads/instagrapi_settings.json` 都已在 `.gitignore` 中）。
- 提交 `.env.example` 作為模板，實際值改用 Railway 變數設定。

#### 方法一：使用 sessionid（推薦）
最簡單穩定的方式，只需提供一個 sessionid 字串：

```powershell
# 1. 在本機完成一次 IG 登入
python autopost.py

# 2. 提取 sessionid
pwsh -File scripts/extract_sessionid.ps1

# 3. 複製輸出的指令到 Railway 執行
railway variables set IG_SESSIONID "你的sessionid"
```

#### 方法二：批次設定所有變數
使用內建腳本產生所有 Railway 變數設定指令：

```powershell
# 在專案根目錄執行（Windows PowerShell）
pwsh -File scripts/export_to_railway.ps1

# 事前準備（安裝 Railway CLI 並連線）
npm i -g @railway/cli
railway login
railway link
```

- 將腳本輸出的 `railway variables set ...` 指令逐行執行，即可把本機的設定（OpenAI、Facebook、Instagram、App 參數）安全地同步到 Railway。

#### 常見問題
**Q: Railway 顯示 JSON 格式錯誤？**
- 不要使用 `IG_SETTINGS_JSON`，改用 `IG_SESSIONID`（更簡單）。

**Q: Railway 登入失敗提示 IP 被封？**
- 在本機完成登入與驗證，提取 `IG_SESSIONID` 供 Railway 使用。
- 可選：設定 `IG_PROXY` 使用代理伺服器。

**Q: sessionid 會過期嗎？**
- 會，但通常可用數週至數月。過期後重新在本機登入並提取新 sessionid 即可。

## 授權
此專案僅供學習參考使用。

## 社群媒體連結
- Facebook：https://www.facebook.com/codingrdx/
- Twitter：https://twitter.com/venom_rdx


