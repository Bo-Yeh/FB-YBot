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
]

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
    """
    優先找出「醫療 / 健康 / 生活」相關的新聞
    找不到再回傳第一篇
    """

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=20) as response:
                if response.status != 200:
                    print('網頁載入失敗:', response.status)
                    return None
                html = await response.text()

        except Exception as ex:
            print('setn_fetch_url 請求失敗:', ex)
            return None

    soup = BeautifulSoup(html, 'html.parser')

    # 抓所有文章區塊
    articles = soup.find_all('h3', class_='view-li-title')

    if not articles:
        print("找不到新聞標題")
        return None

    fallback_url = None

    for h3 in articles:
        a_tag = h3.find('a')
        if not a_tag:
            continue

        title = a_tag.get_text(strip=True)
        href = a_tag.get('href', '').strip()

        if not href:
            continue

        if href.startswith(('http://', 'https://')):
            full_url = href
        else:
            full_url = urljoin(url, href)

        # 設定第一篇做備用
        if fallback_url is None:
            fallback_url = full_url

        # 有沒有命中健康醫療關鍵字
        if is_health_related(title):
            print(f"✅ 命中健康新聞：{title}")
            return full_url
        else:
            print(f"⏭️  跳過：{title}")

    # 如果都沒有命中，使用第一篇
    print("⚠️ 未找到健康相關新聞，使用第一篇")
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