from urllib.parse import urljoin
from bs4 import BeautifulSoup
import aiohttp
import re

# 你可以自己擴充這些關鍵字
KEYWORDS = [
    "醫療", "健康", "醫師", "醫院", "診所", "疫苗", "流感", "癌症", "中醫",
    "健保", "過敏", "感冒", "糖尿病", "血壓", "減肥", "保健", "作息",
    "壓力", "焦慮", "失眠", "健身", "飲食", "營養", "養生", "睡眠",
    "運動", "瑜珈", "伸展", "放鬆", "心理", "療癒", "生活","衛生","醫:","營養師","脂肪","心臟","肺炎","新冠","肺炎","新冠肺炎","阿茲海默"
    "肺癌","中風","骨質疏鬆","關節炎","自律神經","憂鬱症","失智症","帕金森氏症","腦中風","心肌梗塞","高血壓","高血脂","痛風","肝炎","腎臟病","胃潰瘍","腸胃炎","過動症","過敏性鼻炎"
    "哮喘","乳癌","子宮頸癌","大腸癌","攝護腺癌","甲狀腺","更年期","月經不調","不孕症","試管嬰兒","避孕","性病","愛滋病","牙周病","蛀牙","視力","聽力","失聰","白內障","青光眼"
    "罹癌","猝死","安眠藥","抗生素","止痛藥","疫苗接種","流感疫苗","新冠疫苗","基因檢測","健康檢查","體檢","健保卡","醫療保險"
]

# 新聞來源設定
NEWS_SOURCES = {
    "setn": {
        "name": "三立新聞網",
        "url": "https://www.setn.com/ViewAll.aspx",
        "health_section": "https://health.setn.com/"
    },
    "udn": {
        "name": "聯合新聞網",
        "url": "https://health.udn.com/health/index",  # 元氣網健康頻道
        "health_section": "https://health.udn.com/health/index"
    },
    "cna": {
        "name": "中央社",
        "url": "https://www.cna.com.tw/list/ahel.aspx",  # 生活頻道
        "health_section": "https://www.cna.com.tw/list/ahel.aspx"
    },
    "ltn": {
        "name": "自由時報",
        "url": "https://health.ltn.com.tw/",  # 健康網
        "health_section": "https://health.ltn.com.tw/"
    },
    "tvbs": {
        "name": "TVBS新聞網",
        "url": "https://health.tvbs.com.tw/",
        "health_section": "https://health.tvbs.com.tw/"
    }
}

def is_health_related(text: str) -> bool:
    if not text:
        return False
    for keyword in KEYWORDS:
        if keyword in text:
            return True
    return False


async def getnews(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=20) as inner_response:
            if inner_response.status == 200:
                inner_html = await inner_response.text()

                soup = BeautifulSoup(inner_html, 'html.parser')

                # 抓文章本體
                word = soup.find_all('article')

                titles1 = []
                for title_tag in word:
                    title1 = title_tag.text.strip()
                    remove = "我是廣告 請繼續往下閱讀"
                    title1 = title1.replace(remove, "")

                    lines = title1.splitlines()
                    title1 = '\n'.join(line for line in lines if line.strip())
                    titles1.append(title1)

                return titles1

            else:
                print(f"無法獲取網頁內容，狀態碼：{inner_response.status}")
                return ["讀取失敗"]


async def setn_fetch_url(url):
    """抓取三立新聞網健康相關新聞"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=20) as response:
                if response.status != 200:
                    print('[SETN] 網頁載入失敗:', response.status)
                    return None
                html = await response.text()
        except Exception as ex:
            print('[SETN] 請求失敗:', ex)
            return None

    soup = BeautifulSoup(html, 'html.parser')

    # 針對健康專區的選擇器
    articles = soup.select('div.news-item a, div.newsItems a, h3.view-li-title a, article a[href*="/news/"]')
    
    if not articles:
        print("[SETN] 找不到新聞標題")
        return None

    fallback_url = None

    for a_tag in articles:
        if not a_tag:
            continue

        title = a_tag.get_text(strip=True)
        href = a_tag.get('href', '').strip()

        if not href or len(title) < 5:
            continue

        if href.startswith(('http://', 'https://')):
            full_url = href
        else:
            full_url = urljoin(url, href)

        # 過濾非新聞連結
        if '/news/' not in full_url and '/News/' not in full_url:
            continue

        if fallback_url is None:
            fallback_url = full_url

        if is_health_related(title):
            print(f"✅ [SETN] 命中健康新聞：{title}")
            return full_url
        else:
            print(f"⏭️  [SETN] 跳過：{title}")

    print("⚠️ [SETN] 未找到健康相關新聞，使用第一篇")
    return fallback_url

async def fetch_news_preview(url):
    """
    取得新聞 og:image（縮圖）
    """
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=20) as r:
                html = await r.text()
        except:
            return None

    soup = BeautifulSoup(html, "html.parser")

    # 1. OG IMAGE
    og_img = soup.find("meta", property="og:image")
    if og_img and og_img.get("content"):
        return og_img.get("content")

    # 2. Twitter image
    tw_img = soup.find("meta", property="twitter:image")
    if tw_img and tw_img.get("content"):
        return tw_img.get("content")

    return None


# ==================== 聯合新聞網 UDN ====================
async def udn_fetch_url(url):
    """抓取聯合新聞網健康相關新聞"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=20) as response:
                if response.status != 200:
                    print(f'[UDN] 網頁載入失敗: {response.status}')
                    return None
                html = await response.text()
        except Exception as ex:
            print(f'[UDN] 請求失敗: {ex}')
            return None

    soup = BeautifulSoup(html, 'html.parser')
    
    # UDN 的文章列表通常在 dt 或 h2 標籤中
    articles = soup.find_all(['dt', 'h2', 'h3'], class_=lambda x: x and ('story' in x or 'title' in x))
    
    if not articles:
        # 備選方案：找所有連結
        articles = soup.select('a[href*="/story/"]')
    
    if not articles:
        print("[UDN] 找不到新聞標題")
        return None

    fallback_url = None

    for article in articles:
        a_tag = article.find('a') if article.name != 'a' else article
        if not a_tag:
            continue

        title = a_tag.get_text(strip=True)
        href = a_tag.get('href', '').strip()

        if not href or len(title) < 5:
            continue

        full_url = urljoin(url, href) if not href.startswith('http') else href

        if fallback_url is None:
            fallback_url = full_url

        if is_health_related(title):
            print(f"✅ [UDN] 命中健康新聞：{title}")
            return full_url
        else:
            print(f"⏭️  [UDN] 跳過：{title}")

    print("⚠️ [UDN] 未找到健康相關新聞，使用第一篇")
    return fallback_url


# ==================== 中央社 CNA ====================
async def cna_fetch_url(url):
    """抓取中央社健康相關新聞"""
    async with aiohttp.ClientSession() as session:
        try:
            # 忽略 SSL 驗證問題
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, timeout=20) as response:
                    if response.status != 200:
                        print(f'[CNA] 網頁載入失敗: {response.status}')
                        return None
                    html = await response.text()
        except Exception as ex:
            print(f'[CNA] 請求失敗: {ex}')
            return None

    soup = BeautifulSoup(html, 'html.parser')
    
    # CNA 的文章列表
    articles = soup.find_all(['h2', 'div', 'a'], class_=lambda x: x and ('title' in x.lower() or 'mainList' in x))
    
    if not articles:
        articles = soup.select('a[href*="/news/"], div.listInfo a')
    
    if not articles:
        print("[CNA] 找不到新聞標題")
        return None

    fallback_url = None

    for article in articles:
        a_tag = article.find('a') if article.name != 'a' else article
        if not a_tag:
            continue

        title = a_tag.get_text(strip=True)
        href = a_tag.get('href', '').strip()

        if not href or len(title) < 5:
            continue

        full_url = urljoin(url, href) if not href.startswith('http') else href

        if fallback_url is None:
            fallback_url = full_url

        if is_health_related(title):
            print(f"✅ [CNA] 命中健康新聞：{title}")
            return full_url
        else:
            print(f"⏭️  [CNA] 跳過：{title}")

    print("⚠️ [CNA] 未找到健康相關新聞，使用第一篇")
    return fallback_url


# ==================== 自由時報 LTN ====================
async def ltn_fetch_url(url):
    """抓取自由時報健康相關新聞"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=20) as response:
                if response.status != 200:
                    print(f'[LTN] 網頁載入失敗: {response.status}')
                    return None
                html = await response.text()
        except Exception as ex:
            print(f'[LTN] 請求失敗: {ex}')
            return None

    soup = BeautifulSoup(html, 'html.parser')
    
    # 自由時報的文章列表
    articles = soup.find_all(['h3', 'h2', 'div'], class_=lambda x: x and ('title' in x.lower() or 'text' in x))
    
    if not articles:
        articles = soup.select('a[href*="/article/"]')
    
    if not articles:
        print("[LTN] 找不到新聞標題")
        return None

    fallback_url = None

    for article in articles:
        a_tag = article.find('a') if article.name != 'a' else article
        if not a_tag:
            continue

        title = a_tag.get_text(strip=True)
        href = a_tag.get('href', '').strip()

        if not href or len(title) < 5:
            continue

        full_url = urljoin(url, href) if not href.startswith('http') else href

        if fallback_url is None:
            fallback_url = full_url

        if is_health_related(title):
            print(f"✅ [LTN] 命中健康新聞：{title}")
            return full_url
        else:
            print(f"⏭️  [LTN] 跳過：{title}")

    print("⚠️ [LTN] 未找到健康相關新聞，使用第一篇")
    return fallback_url


# ==================== 統一介面：根據來源選擇爬蟲 ====================
async def fetch_news_url(source="setn"):
    """
    統一的新聞抓取介面
    Args:
        source: 新聞來源代碼 (setn/udn/cna/ltn)
    Returns:
        新聞URL或None
    """
    if source not in NEWS_SOURCES:
        print(f"⚠️ 不支援的新聞來源: {source}")
        return None
    
    source_config = NEWS_SOURCES[source]
    url = source_config["health_section"]
    
    print(f"\n📰 抓取 {source_config['name']} 新聞...")
    
    if source == "setn":
        return await setn_fetch_url(url)
    elif source == "udn":
        return await udn_fetch_url(url)
    elif source == "cna":
        return await cna_fetch_url(url)
    elif source == "ltn":
        return await ltn_fetch_url(url)
    else:
        return None


# ==================== 輪詢多個來源 ====================
async def fetch_news_from_multiple_sources(sources=None):
    """
    從多個新聞來源輪詢抓取
    Args:
        sources: 新聞來源列表，預設為所有來源
    Returns:
        (news_url, source_name) 或 (None, None)
    """
    if sources is None:
        sources = list(NEWS_SOURCES.keys())
    
    import random
    random.shuffle(sources)  # 隨機順序避免總是同一家
    
    for source in sources:
        try:
            news_url = await fetch_news_url(source)
            if news_url:
                return news_url, NEWS_SOURCES[source]["name"]
        except Exception as e:
            print(f"⚠️ {NEWS_SOURCES[source]['name']} 抓取失敗: {e}")
            continue
    
    return None, None