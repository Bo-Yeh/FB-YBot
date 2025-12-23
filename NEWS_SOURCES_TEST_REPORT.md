# 多家新聞來源爬蟲測試結果

## 測試日期
2025年12月23日

## 測試來源
1. 三立新聞網 (setn) - https://health.setn.com/
2. 聯合新聞網 (udn) - https://health.udn.com/
3. 中央社 (cna) - https://www.cna.com.tw/
4. 自由時報 (ltn) - https://health.ltn.com.tw/
5. TVBS新聞網 (tvbs) - https://health.tvbs.com.tw/

## 測試結果

### ✅ 成功運作
- **自由時報 (LTN)**: 可穩定抓取健康新聞URL，選擇器正常運作

### ⚠️ 部分成功/需改進
- **三立新聞網 (SETN)**: health.setn.com 頁面結構可能需要動態載入或更新選擇器
- **聯合新聞網 (UDN)**: health.udn.com 能夠連線但選擇器需要調整
- **中央社 (CNA)**: SSL 憑證問題已解決，選擇器需要優化
- **TVBS**: 新增來源，待測試優化

## 功能特色
1. ✅ 多來源輪詢機制
2. ✅ 健康關鍵字過濾
3. ✅ 隨機來源順序（避免偏重單一來源）
4. ✅ 統一介面 `fetch_news_from_multiple_sources()`
5. ✅ 詳細的日誌輸出

## 使用方式

### 單一來源抓取
```python
from spider import fetch_news_url

news_url = await fetch_news_url("ltn")  # 自由時報
```

### 多來源輪詢
```python
from spider import fetch_news_from_multiple_sources

news_url, source_name = await fetch_news_from_multiple_sources()
print(f"從 {source_name} 抓取: {news_url}")
```

### 指定來源列表
```python
# 只從特定來源中選擇
news_url, source = await fetch_news_from_multiple_sources(["ltn", "setn"])
```

## 測試指令
```bash
# 快速測試所有來源連線
python test_news_sources.py 4

# 完整測試所有來源
python test_news_sources.py 1

# 測試單一來源
python test_news_sources.py 2

# 測試多來源輪詢
python test_news_sources.py 3
```

## 後續改進方向
1. 針對SETN、UDN、CNA優化選擇器
2. 添加更多新聞來源（如ETtoday、NOWnews等）
3. 實作動態網頁支援（Selenium/Playwright）
4. 新聞內容結構化解析
5. 增加錯誤重試機制

## 已驗證功能
- ✅ 健康關鍵字過濾正常運作
- ✅ URL正規化處理正確
- ✅ 多來源輪詢機制穩定
- ✅ SSL憑證問題處理
- ✅ 錯誤處理與日誌輸出完善
