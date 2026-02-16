import requests
import facebook
import openai
import asyncio
import random
import time
import json
import re
import os
import sys
from spider import getnews, setn_fetch_url, fetch_news_preview
from instagrapi import Client
from instagrapi.exceptions import LoginRequired

# ----------------- 載入設定（環境變數優先，若無則 fallback 到 config.json） -----------------
def load_config():
    # 環境變數
    API_KEY = os.getenv("API_KEY")
    FB_TOKEN = os.getenv("FB_TOKEN")
    NEWS = os.getenv("NEWS")
    MODE = os.getenv("MODE")
    POST_DELAY_MIN = os.getenv("POST_DELAY_MIN")
    POST_DELAY_MAX = os.getenv("POST_DELAY_MAX")
    IG_USERNAME = os.getenv("IG_USERNAME")
    IG_PASSWORD = os.getenv("IG_PASSWORD")
    IG_SESSIONID = os.getenv("IG_SESSIONID")
    IG_SETTINGS_PATH = os.getenv("IG_SETTINGS_PATH")
    IG_SETTINGS_JSON = os.getenv("IG_SETTINGS_JSON")
    IG_PROXY = os.getenv("IG_PROXY")
    POST_TO_FACEBOOK = os.getenv("POST_TO_FACEBOOK")
    POST_TO_INSTAGRAM = os.getenv("POST_TO_INSTAGRAM")

    # 若至少有一個必要參數不存在，嘗試從 config.json 讀取（方便本地測試）
    if not (API_KEY and FB_TOKEN and NEWS and MODE):
        try:
            with open("config.json", encoding="utf-8") as f:
                data = json.load(f)
            API_KEY = API_KEY or data.get("API_KEY")
            FB_TOKEN = FB_TOKEN or data.get("FB_TOKEN")
            NEWS = NEWS or data.get("NEWS")
            MODE = MODE or data.get("MODE")
            POST_DELAY_MIN = POST_DELAY_MIN or data.get("POST_DELAY_MIN")
            POST_DELAY_MAX = POST_DELAY_MAX or data.get("POST_DELAY_MAX")
            IG_USERNAME = IG_USERNAME or data.get("IG_USERNAME")
            IG_PASSWORD = IG_PASSWORD or data.get("IG_PASSWORD")
            # 這些可選項通常在雲端以環境變數提供，若存在於 config.json 也允許讀取
            IG_SESSIONID = IG_SESSIONID or data.get("IG_SESSIONID")
            IG_SETTINGS_PATH = IG_SETTINGS_PATH or data.get("IG_SETTINGS_PATH")
            IG_SETTINGS_JSON = IG_SETTINGS_JSON or data.get("IG_SETTINGS_JSON")
            IG_PROXY = IG_PROXY or data.get("IG_PROXY")
            POST_TO_FACEBOOK = POST_TO_FACEBOOK if POST_TO_FACEBOOK is not None else data.get("POST_TO_FACEBOOK")
            POST_TO_INSTAGRAM = POST_TO_INSTAGRAM if POST_TO_INSTAGRAM is not None else data.get("POST_TO_INSTAGRAM")
        except FileNotFoundError:
            # 沒有 config.json 也 OK，之後會檢查必要變數
            pass

    # 型別轉換與預設值
    try:
        POST_DELAY_MIN = int(POST_DELAY_MIN) if POST_DELAY_MIN is not None else 30 * 60
    except ValueError:
        POST_DELAY_MIN = 30 * 60

    try:
        POST_DELAY_MAX = int(POST_DELAY_MAX) if POST_DELAY_MAX is not None else 3 * 60 * 60
    except ValueError:
        POST_DELAY_MAX = 3 * 60 * 60

    MODE = MODE or "setn"
    
    # 轉換布林值
    if isinstance(POST_TO_FACEBOOK, str):
        POST_TO_FACEBOOK = POST_TO_FACEBOOK.lower() in ['true', '1', 'yes']
    if isinstance(POST_TO_INSTAGRAM, str):
        POST_TO_INSTAGRAM = POST_TO_INSTAGRAM.lower() in ['true', '1', 'yes']
    
    # 預設值
    POST_TO_FACEBOOK = POST_TO_FACEBOOK if POST_TO_FACEBOOK is not None else True
    POST_TO_INSTAGRAM = POST_TO_INSTAGRAM if POST_TO_INSTAGRAM is not None else False

    return (
        API_KEY,
        FB_TOKEN,
        NEWS,
        MODE,
        POST_DELAY_MIN,
        POST_DELAY_MAX,
        IG_USERNAME,
        IG_PASSWORD,
        IG_SESSIONID,
        IG_SETTINGS_PATH,
        IG_SETTINGS_JSON,
        IG_PROXY,
        POST_TO_FACEBOOK,
        POST_TO_INSTAGRAM,
    )

API_KEY, FB_TOKEN, NEWS, MODE, POST_DELAY_MIN, POST_DELAY_MAX, IG_USERNAME, IG_PASSWORD, IG_SESSIONID, IG_SETTINGS_PATH, IG_SETTINGS_JSON, IG_PROXY, POST_TO_FACEBOOK, POST_TO_INSTAGRAM = load_config()

# 檢查必要變數
missing = []
if not API_KEY:
    missing.append("API_KEY")
if not FB_TOKEN:
    missing.append("FB_TOKEN")
if not NEWS:
    missing.append("NEWS")
if missing:
    print("錯誤：缺少必要環境變數或 config.json 欄位：", ", ".join(missing))
    print("請在 Railway 的 Environment Variables 中設定，或放入本機 config.json。")
    sys.exit(1)

# init FB graph
if POST_TO_FACEBOOK:
    graph = facebook.GraphAPI(access_token=FB_TOKEN)
else:
    graph = None

# init Instagram client（優先使用既有 session / settings 以降低雲端登入驗證）
ig_client = None
if POST_TO_INSTAGRAM and IG_USERNAME:
    try:
        c = Client()

        # 設定 Proxy（可選）
        if IG_PROXY:
            try:
                c.set_proxy(IG_PROXY)
                print("🔌 已設定 IG Proxy")
            except Exception as e:
                print(f"⚠️ 設定 Proxy 失敗: {e}")

        # 既有設定檔的儲存位置（預設到 downloads/ 方便持久化）
        settings_dump_path = IG_SETTINGS_PATH or os.path.join("downloads", "instagrapi_settings.json")
        try:
            os.makedirs(os.path.dirname(settings_dump_path), exist_ok=True)
        except Exception:
            pass

        # 1) 先嘗試使用 sessionid 直接登入（最穩定）
        if not ig_client and IG_SESSIONID:
            try:
                c.login_by_sessionid(IG_SESSIONID)
                ig_client = c
                print("✅ Instagram 透過 sessionid 登入成功")
                try:
                    c.dump_settings(settings_dump_path)
                except Exception as e:
                    print(f"⚠️ 儲存 IG 設定失敗: {e}")
            except Exception as e:
                print(f"⚠️ sessionid 登入失敗: {e}")

        # 2) 若未登入，嘗試載入既有 settings（JSON 或檔案路徑）
        if not ig_client:
            settings_loaded = False
            if IG_SETTINGS_JSON:
                try:
                    # Railway 環境變數可能有單引號包裹或轉義問題，先清理
                    cleaned_json = IG_SETTINGS_JSON.strip()
                    # 移除可能的外層單引號
                    if cleaned_json.startswith("'") and cleaned_json.endswith("'"):
                        cleaned_json = cleaned_json[1:-1]
                    # 嘗試解析
                    settings = json.loads(cleaned_json)
                    c.set_settings(settings)
                    settings_loaded = True
                    print("✅ 已載入 IG 設定 (JSON)")
                except json.JSONDecodeError as e:
                    print(f"⚠️ IG_SETTINGS_JSON 格式錯誤: {e}")
                    print(f"提示：請確認 Railway 變數中的 JSON 格式正確，建議改用 IG_SESSIONID")
                except Exception as e:
                    print(f"⚠️ 載入 IG 設定(JSON)失敗: {e}")
            elif settings_dump_path and os.path.exists(settings_dump_path):
                try:
                    c.load_settings(settings_dump_path)
                    settings_loaded = True
                    print(f"✅ 已載入 IG 設定檔: {settings_dump_path}")
                except Exception as e:
                    print(f"⚠️ 載入 IG 設定檔失敗: {e}")

            # 3) 使用帳密登入（若提供），重用已載入的裝置指紋與設定以降低挑戰機率
            if IG_PASSWORD:
                try:
                    c.login(IG_USERNAME, IG_PASSWORD)
                    ig_client = c
                    print("✅ Instagram 登入成功")
                    try:
                        c.dump_settings(settings_dump_path)
                        print(f"✅ 已儲存 IG 設定至: {settings_dump_path}")
                        
                        # 提取 sessionid 供後續使用
                        try:
                            settings = c.get_settings()
                            sessionid = settings.get("authorization_data", {}).get("sessionid")
                            if sessionid:
                                print(f"\n💡 建議：將以下 sessionid 設定到 Railway 的 IG_SESSIONID 變數：")
                                print(f"   {sessionid}\n")
                        except Exception:
                            pass
                    except Exception as e:
                        print(f"⚠️ 儲存 IG 設定失敗: {e}")
                except Exception as e:
                    print(f"⚠️ Instagram 登入失敗: {e}")
                    print("建議解決方案：")
                    print("1. 在本機完成登入後，從 downloads/instagrapi_settings.json 取得 sessionid")
                    print("2. 在 Railway 設定 IG_SESSIONID 變數（而非完整 JSON）")
                    print("3. 若持續失敗，設定 IG_PROXY 使用代理伺服器")
                    ig_client = None
            else:
                print("⚠️ 未提供 IG_PASSWORD，無法進行帳密登入")
                print("建議：在 Railway 設定 IG_SESSIONID 或 IG_SETTINGS_JSON")

    except Exception as e:
        print(f"⚠️ 初始化 Instagram 客戶端失敗: {e}")
        ig_client = None

# 驗證並確保 IG 已登入（避免 403 login_required）
def ensure_ig_authenticated() -> bool:
    """
    檢查並確保 ig_client 處於已登入狀態；必要時重試登入。
    回傳 True 表示可進行上傳；False 表示登入維持失敗。
    """
    global ig_client
    if not POST_TO_INSTAGRAM or not ig_client:
        return False

    def _is_logged_in() -> bool:
        """以輕量方式驗證登入：優先使用私有 API (`account_info`)，避免 public lookup 導致 429。
        如果 `IG_USERNAME` 看起來像 email (包含 '@')，則不要用 username 做 public 查詢。"""
        try:
            # 優先使用 account_info()（私有 API，依賴已登入 session）
            try:
                ig_client.account_info()
                return True
            except LoginRequired:
                return False
            except Exception:
                # 若 account_info 不可用，退回到檢查 sessionid
                pass

            # 避免以 email 做 public lookup，這會觸發 /web_profile_info 與 429
            if IG_USERNAME and "@" not in IG_USERNAME:
                try:
                    ig_client.user_info_by_username(IG_USERNAME)
                    return True
                except LoginRequired:
                    return False
                except Exception:
                    # public lookup 失敗則回傳 False（但不要 raise，讓上層處理）
                    return False

            # 最後以 sessionid 作為弱驗證
            return bool(getattr(ig_client, "sessionid", None))
        except Exception:
            return False

    try:
        # 先嘗試現況
        if _is_logged_in():
            return True

        # 嘗試載入 settings（僅接受 instagrapi 產生過的結構，避免異常 key 如 pinned_channels_info）
        try:
            # 優先 JSON 變數
            if IG_SETTINGS_JSON:
                cleaned_json = IG_SETTINGS_JSON.strip()
                if cleaned_json.startswith("'") and cleaned_json.endswith("'"):
                    cleaned_json = cleaned_json[1:-1]
                settings = json.loads(cleaned_json)
                if isinstance(settings, dict) and (
                    "authorization_data" in settings and "device_settings" in settings
                ):
                    ig_client.set_settings(settings)
                else:
                    # 不是 instagrapi 的設定格式就忽略
                    pass
            else:
                settings_path = IG_SETTINGS_PATH or os.path.join("downloads", "instagrapi_settings.json")
                if os.path.exists(settings_path):
                    ig_client.load_settings(settings_path)
        except Exception:
            # 設定載入失敗不影響後續登入嘗試
            pass

        # 以 sessionid 重新登入（環境變數或從 settings 中提取）
        sessionid = None
        if IG_SESSIONID:
            sessionid = IG_SESSIONID
        else:
            # 從 JSON 設定或檔案提取 sessionid
            try:
                if IG_SETTINGS_JSON:
                    sj = json.loads(IG_SETTINGS_JSON.strip().strip("'"))
                    sessionid = sj.get("authorization_data", {}).get("sessionid")
                if not sessionid:
                    settings_path = IG_SETTINGS_PATH or os.path.join("downloads", "instagrapi_settings.json")
                    if os.path.exists(settings_path):
                        with open(settings_path, "r", encoding="utf-8") as f:
                            s = json.load(f)
                        sessionid = s.get("authorization_data", {}).get("sessionid")
            except Exception:
                sessionid = None

        if sessionid:
            try:
                ig_client.login_by_sessionid(sessionid)
                if _is_logged_in():
                    return True
            except Exception as e:
                # 更精確地處理 429 / MaxRetryError 類型錯誤，避免大量重試
                msg = str(e)
                if "429" in msg or "too many 429" in msg or "MaxRetryError" in msg:
                    print(f"⚠️ public requests 被速率限制 (429)：{e}")
                    return False
                print(f"⚠️ 透過 sessionid 重新登入失敗: {e}")

        # 帳密登入（若提供）
        if IG_USERNAME and IG_PASSWORD:
            try:
                ig_client.login(IG_USERNAME, IG_PASSWORD)
                if _is_logged_in():
                    # 成功後儲存設定並提示 sessionid
                    try:
                        settings_dump_path = os.path.join("downloads", "instagrapi_settings.json")
                        os.makedirs(os.path.dirname(settings_dump_path), exist_ok=True)
                        ig_client.dump_settings(settings_dump_path)
                        # 顯示 sessionid 便於雲端使用
                        try:
                            settings = ig_client.get_settings()
                            sid = settings.get("authorization_data", {}).get("sessionid")
                            if sid:
                                print("\n💡 建議：將以下 sessionid 設定到 Railway 的 IG_SESSIONID 變數：")
                                print(f"   {sid}\n")
                        except Exception:
                            pass
                    except Exception:
                        pass
                    return True
            except Exception as e:
                # 如果是 public request 的 retry 錯誤，提示並回傳 False
                msg = str(e)
                if "429" in msg or "too many 429" in msg or "MaxRetryError" in msg:
                    print(f"⚠️ public requests 被速率限制 (429)：{e}")
                    return False
                print(f"❌ 帳密登入失敗: {e}")
                return False

        print("⚠️ 無法驗證 IG 登入狀態（缺少可用的 sessionid 或密碼）")
        return False
    except Exception as e:
        print(f"⚠️ 檢查 IG 登入狀態失敗: {e}")
        return False

# 延遲時間
def compute_delay():
    _min = float(POST_DELAY_MIN)
    _max = float(POST_DELAY_MAX)
    if _min > _max:
        _min, _max = _max, _min
    return random.uniform(_min, _max)

# GPT Prompt
# prompt = """
# 你是一名專業的醫師，根據新聞撰寫跟新聞相關的內容好像在民眾對話的感覺，
# 請使用繁體中文且吸引人，輸出僅包含內文，不要標題、盡可能簡短明瞭不超過50字。
# """

prompt_with_title = """
你是一名專業的醫師，根據新聞內容生成社群媒體貼文，內容須像與民眾對話的感覺。
請用繁體中文生成以下內容：
1. 短標題：吸引觀眾的精簡標題，10-15字以內，適合放在圖片上
2. 內文：像在跟民眾對話的感覺，簡短明瞭不超過50字

請按照以下格式輸出：
標題：[你的短標題]
內文：[你的內文]
"""

async def text_api(msg: str) -> str:
    """僅生成內文"""
    if not msg:
        return "這段訊息是空的"
    def _call():
        try:
            client = openai.OpenAI(api_key=API_KEY)
            result = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": msg}
                ],
                temperature=1.0,
                max_tokens=200
            )
            # 支援不同回傳格式
            try:
                return result.choices[0].message.content.strip()
            except Exception:
                # fallback: 可能為 dict 形式
                if isinstance(result, dict) and "choices" in result and len(result["choices"])>0:
                    ch = result["choices"][0]
                    if isinstance(ch, dict) and "message" in ch and "content" in ch["message"]:
                        return ch["message"]["content"].strip()
                return "生成失敗"
        except Exception as e:
            print("GPT 發生錯誤:", e)
            return "生成失敗"
    return await asyncio.to_thread(_call)

async def text_api_with_title(msg: str) -> tuple:
    """生成短標題和內文，返回 (標題, 內文)"""
    if not msg:
        return "這段訊息是空的", "這段訊息是空的"
    def _call():
        try:
            client = openai.OpenAI(api_key=API_KEY)
            result = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": prompt_with_title},
                    {"role": "user", "content": msg}
                ],
                temperature=1.0,
                max_tokens=300
            )
            # 支援不同回傳格式
            try:
                content = result.choices[0].message.content.strip()
            except Exception:
                # fallback: 可能為 dict 形式
                if isinstance(result, dict) and "choices" in result and len(result["choices"])>0:
                    ch = result["choices"][0]
                    if isinstance(ch, dict) and "message" in ch and "content" in ch["message"]:
                        content = ch["message"]["content"].strip()
                    else:
                        return "生成失敗", "生成失敗"
                else:
                    return "生成失敗", "生成失敗"
            
            # 解析標題和內文
            lines = content.split('\n')
            title = ""
            text = ""
            
            for line in lines:
                if line.startswith("標題：") or line.startswith("標題:"):
                    title = line.replace("標題：", "").replace("標題:", "").strip()
                elif line.startswith("內文：") or line.startswith("內文:"):
                    text = line.replace("內文：", "").replace("內文:", "").strip()
            
            # 如果解析失敗，嘗試使用整個內容
            if not title or not text:
                # 嘗試按換行分割，第一行當標題，其餘當內文
                parts = content.split('\n', 1)
                if len(parts) == 2:
                    title = parts[0].strip()
                    text = parts[1].strip()
                else:
                    title = content[:15] + "..."  # 取前15字作為標題
                    text = content
            
            return title, text
        except Exception as e:
            print("GPT 發生錯誤:", e)
            return "生成失敗", "生成失敗"
    return await asyncio.to_thread(_call)

async def generate_hashtags(news_content: str) -> str:
    """根據新聞內容生成相關標籤"""
    if not news_content:
        return "#新聞 #健康 #醫療"
    
    def _call():
        try:
            client = openai.OpenAI(api_key=API_KEY)
            result = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": """你是一個社群媒體專家。
根據新聞內容生成相關的繁體中文標籤。
標籤應該：
1. 與新聞主題相關
2. 具有搜尋熱度
3. 每個標籤前面加 #
4. 用空格分隔
5. 數量不限，但建議 5-10 個

只輸出標籤，不要其他解釋。"""},
                    {"role": "user", "content": f"新聞內容：{news_content}"}
                ],
                temperature=0.7,
                max_tokens=200
            )
            hashtags = result.choices[0].message.content.strip()
            # 確保每個標籤都有 #
            if not hashtags.startswith("#"):
                hashtags = "#" + hashtags
            return hashtags
        except Exception as e:
            print(f"生成標籤錯誤: {e}")
            return "#新聞 #健康 #醫療"
    
    return await asyncio.to_thread(_call)

# ================= 發文 ===================
def post_to_facebook(text):
    if not POST_TO_FACEBOOK or not graph:
        return
    try:
        graph.put_object(parent_object='me', connection_name='feed', message=text)
        print("✅ 已發布到 Facebook")
    except Exception as e:
        print("❌ Facebook 發文錯誤:", e)

def get_chinese_font(size):
    """取得繁體中文字體，支援 Windows、Mac、Linux/Railway
    優先使用系統字體，若無則自動下載 Noto Sans TC
    """
    # 常見系統字體路徑（Railway Aptfile 安裝後的路徑在前）
    font_paths = [
        # Railway/Ubuntu 透過 Aptfile 安裝的 Noto CJK
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto-cjk/NotoSansTC-Regular.otf",
        "/usr/share/fonts/truetype/noto/NotoSansTC-Regular.ttf",
        # Windows
        "C:/Windows/Fonts/msjh.ttc",      # 微軟正黑體
        "C:/Windows/Fonts/kaiu.ttf",       # 標楷體
        "C:/Windows/Fonts/mingliu.ttc",    # 細明體
        # Mac
        "/System/Library/Fonts/PingFang.ttc",  # Mac 蘋方體
        # 專案內建字體
        "fonts/NotoSansTC-Regular.ttf",
        "fonts/NotoSansTC-Regular.otf",
    ]
    
    # 嘗試系統字體
    for font_path in font_paths:
        try:
            from PIL import ImageFont
            font = ImageFont.truetype(font_path, size)
            return font
        except:
            continue
    
    # Railway/Linux 環境：下載 Noto Sans TC（多重備援）
    try:
        import urllib.request
        fonts_dir = "fonts"
        os.makedirs(fonts_dir, exist_ok=True)
        font_file = os.path.join(fonts_dir, "NotoSansTC-Regular.ttf")
        
        if not os.path.exists(font_file):
            print("⬇️ 下載繁體中文字體 Noto Sans TC...")
            
            # 多重下載來源（按優先順序嘗試）
            font_urls = [
                # Google Fonts CDN (最穩定)
                "https://raw.githubusercontent.com/google/fonts/main/ofl/notosanstc/NotoSansTC%5Bwght%5D.ttf",
                # GitHub Noto CJK 倉庫
                "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansTC-Regular.otf",
                # jsDelivr CDN 備援
                "https://cdn.jsdelivr.net/gh/notofonts/noto-cjk/Sans/OTF/TraditionalChinese/NotoSansTC-Regular.otf",
            ]
            
            downloaded = False
            for url in font_urls:
                try:
                    print(f"  嘗試來源: {url[:50]}...")
                    urllib.request.urlretrieve(url, font_file)
                    # 驗證檔案大小（避免下載到錯誤頁面）
                    if os.path.getsize(font_file) > 100000:  # 至少 100KB
                        print(f"✅ 字體已下載至: {font_file}")
                        downloaded = True
                        break
                    else:
                        os.remove(font_file)
                except Exception as e:
                    print(f"  ⚠️ 此來源失敗: {e}")
                    if os.path.exists(font_file):
                        os.remove(font_file)
                    continue
            
            if not downloaded:
                raise Exception("所有字體下載來源均失敗")
        
        from PIL import ImageFont
        return ImageFont.truetype(font_file, size)
    except Exception as e:
        print(f"⚠️ 無法載入中文字體: {e}")
        print("建議：請在 Railway 手動設定 apt buildpack 安裝 fonts-noto-cjk")
        from PIL import ImageFont
        return ImageFont.load_default()

def post_to_instagram(text, image_title=None, news_url=None, hashtags=None):
    """發布貼文到 Instagram，生成隨機淺色背景圖片，標題置中，底部提示查看連結
    
    Args:
        text: 貼文內文（如果已經包含連結，則不再添加）
        image_title: 圖片上顯示的短標題（如果沒有提供，則從 text 中提取）
        news_url: 新聞連結（如果 text 已包含則不再添加）
        hashtags: 自動生成的標籤
    """
    if not POST_TO_INSTAGRAM or not ig_client:
        return
    try:
        # 上傳前先確認登入狀態，避免 403 login_required
        if not ensure_ig_authenticated():
            print("❌ IG 未登入，跳過 Instagram 發文")
            return
        from PIL import Image, ImageDraw, ImageFont
        import tempfile
        
        # 生成隨機淺色背景 (RGB 值範圍 200-255)
        bg_r = random.randint(200, 255)
        bg_g = random.randint(200, 255)
        bg_b = random.randint(200, 255)
        bg_color = (bg_r, bg_g, bg_b)
        
        # 創建圖片
        img = Image.new('RGB', (1080, 1080), color=bg_color)
        d = ImageDraw.Draw(img)
        
        # 載入繁體中文字體（跨平台支援）
        font_title = get_chinese_font(85)
        font_footer = get_chinese_font(40)
        font_logo = get_chinese_font(50)
        
        # 繪製頂部 LOGO 文字
        logo_text = "陳醫師談"
        text_color = (40, 40, 40)  # 深灰色文字
        
        try:
            bbox = d.textbbox((0, 0), logo_text, font=font_logo)
            logo_width = bbox[2] - bbox[0]
        except:
            logo_width = len(logo_text) * 25
        
        logo_x = (1080 - logo_width) // 2
        logo_y = 40
        d.text((logo_x, logo_y), logo_text, fill=text_color, font=font_logo)
        
        # 使用短標題或從 text 中提取
        if image_title:
            title_text = image_title
        else:
            title_text = text.replace("🔗 新聞全文：", "").split("http")[0].strip()
        
        # 標題文字智慧換行處理：優先在標點符號（，、：、；）處換行
        # 每行最多15個字（考慮 85px 大字體）
        lines = []
        current_line = ""
        punctuation_marks = ["，", "：", "；", ",", ":", ";"]
        remove_before_break = ["，", "、", ","]

        i = 0
        while i < len(title_text):
            char = title_text[i]

            # 遇到換行符
            if char == '\n':
                if current_line:
                    # 換行前刪除指定標點
                    if current_line and current_line[-1] in remove_before_break:
                        current_line = current_line[:-1]
                    lines.append(current_line)
                current_line = ""
                i += 1
                continue

            current_line += char

            # 優先在標點符號處換行
            if char in punctuation_marks:
                # 換行前刪除指定標點
                if current_line and current_line[-1] in remove_before_break:
                    current_line = current_line[:-1]
                lines.append(current_line)
                current_line = ""
                i += 1
                continue

            # 如果行長達到限制則換行
            if len(current_line) >= 13:
                # 換行前刪除指定標點
                if current_line and current_line[-1] in remove_before_break:
                    current_line = current_line[:-1]
                lines.append(current_line)
                current_line = ""

            i += 1

        # 添加剩餘文字
        if current_line:
            # 換行前刪除指定標點
            if current_line and current_line[-1] in remove_before_break:
                current_line = current_line[:-1]
            lines.append(current_line)

        
        # 計算總高度以垂直置中（考慮頂部 LOGO 和更大字體）
        line_height = 100  # 增加行間距以適應更大的字體
        total_height = len(lines) * line_height
        # 將標題往下移，給 LOGO 留出空間
        start_y = (1080 - total_height) // 2 - 50
        
        # 繪製標題文字 (置中對齊)
        for i, line in enumerate(lines[:8]):  # 最多8行
            # 計算文字寬度以水平置中
            try:
                bbox = d.textbbox((0, 0), line.strip(), font=font_title)
                text_width = bbox[2] - bbox[0]
            except:
                text_width = len(line.strip()) * 30
            
            x = (1080 - text_width) // 2
            y = start_y + i * line_height
            d.text((x, y), line.strip(), fill=text_color, font=font_title)
        
        # 底部提示文字
        footer_text = "查看文章底下連結了解更多"
        try:
            bbox = d.textbbox((0, 0), footer_text, font=font_footer)
            footer_width = bbox[2] - bbox[0]
        except:
            footer_width = len(footer_text) * 20
        
        footer_x = (1080 - footer_width) // 2
        footer_y = 950
        d.text((footer_x, footer_y), footer_text, fill=text_color, font=font_footer)
        
        # 保存臨時圖片
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            img.save(tmp.name, "JPEG", quality=95)
            tmp_path = tmp.name
        
        # 準備 Instagram 貼文內容
        # 如果 text 已經包含連結，則不再添加
        caption = text
        
        # 添加標籤
        if hashtags:
            caption = f"{caption}\n\n{hashtags}"
        else:
            caption = f"{caption}\n\n#新聞 #健康 #醫療"
        
        # 發布到 Instagram
        # 1) 上傳前先確保 session 有效並做暖機/模擬讀取行為
        try:
            if not ensure_ig_authenticated():
                print("⚠️ IG 未驗證，跳過 Instagram 發文")
            else:
                # 暖機：少量讀取操作以確認 session 活著
                try:
                    print("🔎 發文前執行 pre-upload 檢查: account_info() ...", end="", flush=True)
                    ig_client.account_info()
                    print(" ✅")
                except Exception:
                    print(" ⚠️ (account_info 失敗，繼續)")

                try:
                    print("🔎 pre-upload 檢查: user_info() ...", end="", flush=True)
                    ig_client.user_info(ig_client.user_id)
                    print(" ✅")
                except Exception:
                    print(" ⚠️ (user_info 失敗，繼續)")

                # 等待 5-15 分鐘以降低驗證/風控觸發（可改為環境變數）
                wait_seconds = random.randint(5*60, 15*60)
                print(f"⏳ 上傳前等待 {wait_seconds} 秒（5-15 分鐘間隨機）以暖機與模擬人類行為...")
                for _ in range(0, wait_seconds, 10):
                    time.sleep(10)

                # 嘗試上傳，並針對常見挑戰做明確處理
                try:
                    ig_client.photo_upload(tmp_path, caption)
                    print("✅ 已發布到 Instagram")
                except Exception as e:
                    msg = str(e)
                    # 檢查是否是挑戰或驗證型錯誤
                    if "challenge_required" in msg or "challenge" in msg or (hasattr(e, 'response') and getattr(e.response, 'status_code', None) == 412):
                        print(f"❌ Instagram 發文被拒（challenge_required / 412）：{msg}")
                        print("建議：在手機/桌面版 Instagram 完成挑戰驗證，或使用本機重新登入取得新的 sessionid。跳過此次發文。")
                    elif "login_required" in msg or "LoginRequired" in msg:
                        print("⚠️ 上傳遭到 login_required，嘗試重新登入後重試一次...")
                        if ensure_ig_authenticated():
                            try:
                                ig_client.photo_upload(tmp_path, caption)
                                print("✅ 重新登入後已發布到 Instagram")
                            except Exception as e2:
                                print(f"❌ 第二次上傳失敗: {e2}")
                        else:
                            print("❌ 重新登入失敗，跳過 Instagram 發文")
                    else:
                        print(f"❌ Instagram 發文錯誤: {e}")
        except Exception as e:
            print(f"❌ 發文前準備或上傳流程發生錯誤: {e}")
        
        # 刪除臨時文件
        try:
            os.remove(tmp_path)
        except:
            pass
            
    except Exception as e:
        print(f"❌ Instagram 發文錯誤: {e}")

def post_to_facebook_with_link(text: str, news_url: str):
    """
    使用 Graph API 的 feed endpoint 加上 link 參數，讓 FB 嘗試自動產生連結預覽（og:image）
    如果失敗則退回純文字+連結。
    """
    if not POST_TO_FACEBOOK or not graph:
        return
    try:
        graph.put_object(
            parent_object='me',
            connection_name='feed',
            message=text,
            link=news_url
        )
        print("✅ 已發布新聞卡片貼文（含縮圖＋連結）")
    except Exception as e:
        print("⚠️ FB 無法產生預覽卡片或發文失敗，改用純文字發文:", e)
        post_to_facebook(f"{text}\n\n🔗 {news_url}")

def post_to_all_platforms(text, image_title=None, news_url=None, hashtags=None):
    """發布到所有啟用的平台
    
    Args:
        text: 貼文內文
        image_title: Instagram 圖片上顯示的短標題
        news_url: 新聞連結
        hashtags: Instagram 使用的標籤
    """
    if POST_TO_FACEBOOK:
        if news_url:
            post_to_facebook_with_link(text, news_url)
        else:
            post_to_facebook(text)
    
    if POST_TO_INSTAGRAM:
        post_to_instagram(text, image_title, news_url, hashtags)

# ================== 三種模式 =================
async def text_auto_post():
    """純文字模式：根據醫療主題生成內容並發布"""
    while True:
        # 生成醫療相關內容
        topic = "請生成一則關於健康或醫療的簡短建議"
        content = await text_api(topic)
        print("\n生成內容:", content)
        post_to_all_platforms(content)
        delay = compute_delay()
        print(f"⏱ 下次發文: {delay:.1f} 秒後")
        await asyncio.sleep(delay)

async def setn_auto_post(url):
    first = True
    while True:
        news_url = await setn_fetch_url(url)
        if not news_url:
            print("抓取新聞失敗，30秒後重試")
            await asyncio.sleep(30)
            continue

        if not first:
            try:
                with open("cache.txt", "r", encoding="utf-8") as f:
                    cached = f.read().strip()
            except:
                cached = ""

            if cached == news_url:
                print("新聞重複，跳過")
                await asyncio.sleep(compute_delay())
                continue

        # 抓文章內容
        news = await getnews(news_url)

        # GPT 生成短標題和貼文文字
        title, text = await text_api_with_title(" ".join(news))
        print(f"\n生成標題: {title}")
        print(f"生成內容: {text}")
        
        # 生成相關標籤
        hashtags = await generate_hashtags(" ".join(news))
        print(f"生成標籤: {hashtags}")
        
        # 內文已包含連結，不需要再添加
        final_msg = f"{text}\n\n🔗 新聞連結：{news_url}"

        # 發布到所有啟用的平台（圖片使用短標題）
        post_to_all_platforms(final_msg, image_title=title, news_url=news_url, hashtags=hashtags)

        with open("cache.txt", "w", encoding="utf-8") as f:
            f.write(news_url)

        first = False
        delay = compute_delay()
        print(f"⏱ 下次檢查: {delay:.1f} 秒後")
        await asyncio.sleep(delay)

async def manual():
    msg = input("輸入主題或網址：")
    if re.match(r'https?://', msg):
        news = await getnews(msg)
        title, content = await text_api_with_title(" ".join(news))
        print(f"\n生成標題: {title}")
        print(f"生成內容: {content}")
        
        # 生成標籤
        hashtags = await generate_hashtags(" ".join(news))
        print(f"生成標籤: {hashtags}")
        
        content = f"{content}\n\n🔗 新聞連結：{msg}"
        news_url = msg
    else:
        title, content = await text_api_with_title(msg)
        print(f"\n生成標題: {title}")
        print(f"生成內容: {content}")
        
        # 生成標籤
        hashtags = await generate_hashtags(msg)
        print(f"生成標籤: {hashtags}")
        
        news_url = None
        
    if input("要發佈嗎？(y/n): ").lower() == "y":
        post_to_all_platforms(content, image_title=title, news_url=news_url)
    await manual()

# ================== 啟動 ===================
if MODE == "text":
    asyncio.run(text_auto_post())
elif MODE == "setn":
    asyncio.run(setn_auto_post(NEWS))
elif MODE == "manual":
    asyncio.run(manual())
else:
    print(" MODE 設定錯誤，只能為 setn / text / manual ")
