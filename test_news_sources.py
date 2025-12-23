# -*- coding: utf-8 -*-
"""
測試多家新聞來源爬蟲功能
"""
import asyncio
import sys
from spider import (
    fetch_news_url,
    fetch_news_from_multiple_sources,
    NEWS_SOURCES,
    getnews
)

async def test_single_source(source):
    """測試單一新聞來源"""
    print(f"\n{'='*70}")
    print(f"測試新聞來源: {NEWS_SOURCES[source]['name']}")
    print(f"{'='*70}")
    
    try:
        news_url = await fetch_news_url(source)
        
        if news_url:
            print(f"\n✅ 成功抓取新聞URL:")
            print(f"   {news_url}")
            
            # 嘗試抓取文章內容
            print(f"\n⬇️  抓取文章內容...")
            content = await getnews(news_url)
            
            if content and len(content) > 0:
                preview = content[0][:200] if len(content[0]) > 200 else content[0]
                print(f"\n📄 文章預覽:")
                print(f"   {preview}...")
                print(f"\n✅ 內容抓取成功 (共 {len(content)} 段)")
            else:
                print(f"\n⚠️  無法抓取文章內容")
                
            return True
        else:
            print(f"\n❌ 無法抓取新聞URL")
            return False
            
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_all_sources():
    """測試所有新聞來源"""
    print(f"\n{'='*70}")
    print("測試所有新聞來源")
    print(f"{'='*70}\n")
    
    results = {}
    
    for source in NEWS_SOURCES.keys():
        success = await test_single_source(source)
        results[source] = success
        await asyncio.sleep(2)  # 避免請求過快
    
    # 總結
    print(f"\n\n{'='*70}")
    print("測試總結")
    print(f"{'='*70}")
    
    for source, success in results.items():
        status = "✅ 成功" if success else "❌ 失敗"
        print(f"{status} - {NEWS_SOURCES[source]['name']} ({source})")
    
    success_count = sum(1 for s in results.values() if s)
    total_count = len(results)
    print(f"\n成功率: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")

async def test_multiple_sources_rotation():
    """測試多來源輪詢功能"""
    print(f"\n\n{'='*70}")
    print("測試多來源輪詢功能")
    print(f"{'='*70}\n")
    
    for i in range(3):
        print(f"\n--- 第 {i+1} 次輪詢 ---")
        news_url, source_name = await fetch_news_from_multiple_sources()
        
        if news_url:
            print(f"✅ 成功從 {source_name} 抓取:")
            print(f"   {news_url}")
        else:
            print(f"❌ 所有來源都失敗")
        
        await asyncio.sleep(2)

async def main():
    """主測試流程"""
    print("\n" + "="*70)
    print("多家新聞來源爬蟲測試")
    print("="*70)
    print("\n支援的新聞來源:")
    for code, info in NEWS_SOURCES.items():
        print(f"  - {info['name']} ({code})")
    
    # 選擇測試模式
    print("\n請選擇測試模式:")
    print("1. 測試所有來源")
    print("2. 測試單一來源")
    print("3. 測試多來源輪詢")
    print("4. 快速測試（僅檢查連線）")
    
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        choice = input("\n輸入選項 (1-4，直接Enter執行全部): ").strip() or "1"
    
    if choice == "1":
        await test_all_sources()
    elif choice == "2":
        print("\n可用來源:", ", ".join(NEWS_SOURCES.keys()))
        source = input("輸入來源代碼 (預設setn): ").strip() or "setn"
        await test_single_source(source)
    elif choice == "3":
        await test_multiple_sources_rotation()
    elif choice == "4":
        print("\n快速連線測試...")
        for source in NEWS_SOURCES.keys():
            print(f"  測試 {NEWS_SOURCES[source]['name']}...", end=" ")
            try:
                news_url = await fetch_news_url(source)
                print("✅" if news_url else "❌")
            except Exception as e:
                print(f"❌ ({e})")
            await asyncio.sleep(1)
    else:
        print("無效選項，執行全部測試")
        await test_all_sources()
    
    print("\n" + "="*70)
    print("測試完成")
    print("="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
