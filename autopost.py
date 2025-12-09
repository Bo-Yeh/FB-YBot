import requests
import facebook
import openai
import asyncio
import random
import json
import re
import os
import sys
from spider import getnews, setn_fetch_url, fetch_news_preview

# ----------------- 載入設定（環境變數優先，若無則 fallback 到 config.json） -----------------
def load_config():
    # 環境變數
    API_KEY = os.getenv("API_KEY")
    FB_TOKEN = os.getenv("FB_TOKEN")
    NEWS = os.getenv("NEWS")
    MODE = os.getenv("MODE")
    POST_DELAY_MIN = os.getenv("POST_DELAY_MIN")
    POST_DELAY_MAX = os.getenv("POST_DELAY_MAX")

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

    return API_KEY, FB_TOKEN, NEWS, MODE, POST_DELAY_MIN, POST_DELAY_MAX

API_KEY, FB_TOKEN, NEWS, MODE, POST_DELAY_MIN, POST_DELAY_MAX = load_config()

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
graph = facebook.GraphAPI(access_token=FB_TOKEN)

# 延遲時間
def compute_delay():
    _min = float(POST_DELAY_MIN)
    _max = float(POST_DELAY_MAX)
    if _min > _max:
        _min, _max = _max, _min
    return random.uniform(_min, _max)

# GPT Prompt
prompt = """
你是一名專業的醫師，根據新聞撰寫跟新聞相關的內容好像在民眾對話的感覺，
請使用繁體中文且吸引人，輸出僅包含內文，不要標題、盡可能簡短明瞭不超過50字。
"""

async def text_api(msg: str) -> str:
    if not msg:
        return "這段訊息是空的"
    def _call():
        try:
            client = openai.OpenAI(api_key=API_KEY)
            result = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": prompt},
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

# ================= 發文 ===================
def post_to_facebook(text):
    try:
        graph.put_object(parent_object='me', connection_name='feed', message=text)
        print("✅ 已發布到 Facebook")
    except Exception as e:
        print("❌ Facebook 發文錯誤:", e)

def post_to_facebook_with_link(text: str, news_url: str):
    """
    使用 Graph API 的 feed endpoint 加上 link 參數，讓 FB 嘗試自動產生連結預覽（og:image）
    如果失敗則退回純文字+連結。
    """
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

# ================== 三種模式 =================
async def text_auto_post():
    while True:
        content = await text_api(prompt)
        print("\n生成內容:", content)
        post_to_facebook(content)
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

        # GPT 生成貼文文字
        text = await text_api(" ".join(news))
        final_msg = f"{text}\n\n🔗 新聞全文：{news_url}"

        # 優先使用 FB 的 link preview 功能（Graph API 的 feed + link）
        post_to_facebook_with_link(final_msg, news_url)

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
        content = await text_api(" ".join(news))
        content += f"\n\n{msg}"
    else:
        content = await text_api(msg)
    print("\n生成內容:", content)
    if input("要發佈嗎？(y/n): ").lower() == "y":
        post_to_facebook(content)
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
