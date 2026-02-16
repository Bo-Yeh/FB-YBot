"""
強化版 IG SessionID 取得腳本
功能：
1. 強制產生全新 session 並匯出 txt
2. 刪除舊的 session 檔案
3. 登入後驗證 session 活著
4. 添加暖機 + 模擬人類行為
5. 登入後等待 5-15 分鐘
6. 執行一些「讀取」動作驗證
"""

import os
import json
import sys
import time
import random
from datetime import datetime
from pathlib import Path
from instagrapi import Client
from instagrapi.exceptions import LoginRequired


def load_credentials():
    """從環境變數或 config.json 加載 IG 認證資訊"""
    username = os.getenv("IG_USERNAME")
    password = os.getenv("IG_PASSWORD")
    proxy = os.getenv("IG_PROXY")
    settings_path = os.getenv("IG_SETTINGS_PATH") or os.path.join("downloads", "instagrapi_settings.json")

    if not (username and password):
        try:
            with open("config.json", encoding="utf-8") as f:
                data = json.load(f)
            username = username or data.get("IG_USERNAME") or data.get("ACCOUNT")
            password = password or data.get("IG_PASSWORD") or data.get("PASSWORD")
            proxy = proxy or data.get("IG_PROXY")
        except FileNotFoundError:
            pass

    return username, password, proxy, settings_path


def delete_old_session_files(settings_path):
    """刪除舊的 session 檔案"""
    print("\n🗑️  正在清理舊的 session 檔案...")
    
    # 刪除 settings JSON 檔案
    if os.path.exists(settings_path):
        try:
            os.remove(settings_path)
            print(f"✅ 已刪除舊設定檔: {settings_path}")
        except Exception as e:
            print(f"⚠️  刪除舊設定檔失敗: {e}")
    
    # 刪除 downloads 目錄下的其他可能的舊 session 檔案
    downloads_dir = os.path.dirname(settings_path)
    if os.path.exists(downloads_dir):
        for file in os.listdir(downloads_dir):
            if file.startswith("instagrapi_settings") and file.endswith(".json"):
                old_file = os.path.join(downloads_dir, file)
                if old_file != settings_path:
                    try:
                        os.remove(old_file)
                        print(f"✅ 已刪除: {old_file}")
                    except Exception as e:
                        print(f"⚠️  刪除失敗: {e}")


def simulate_human_behavior(cl):
    """暖機 + 模擬人類行為"""
    print("\n🔥 正在進行暖機與人類行為模擬...")
    
    actions = [
        ("自己的帳號資訊", lambda: cl.account_info()),
        ("自己的用戶資訊", lambda: cl.user_info(cl.user_id)),
        ("檢查 sessionid", lambda: getattr(cl, "sessionid", None)),
    ]
    
    success_count = 0
    
    for action_name, action_func in actions:
        try:
            print(f"  ⏳ 正在執行: {action_name}...", end="", flush=True)
            result = action_func()
            print(f" ✅")
            success_count += 1
        except LoginRequired:
            print(f" ❌ (登入已失效)")
        except Exception as e:
            error_msg = str(e)[:50]
            print(f" ⚠️  ({error_msg})")
        
        # 隨機等待 1-3 秒（模擬人類延遲）
        wait_time = random.uniform(1, 3)
        time.sleep(wait_time)
    
    if success_count >= 1:
        print("✅ 暖機完成！")
        return True
    else:
        print("❌ 暖機失敗（所有操作都失敗）")
        return False


def wait_with_countdown(seconds):
    """等待指定秒數，並顯示倒數計時"""
    print(f"\n⏳ 正在等待 {seconds} 秒以確保 session 穩定...", flush=True)
    for remaining in range(seconds, 0, -1):
        print(f"\r⏳ 剩餘時間: {remaining:3d} 秒", end="", flush=True)
        time.sleep(1)
    print("\r✅ 等待完成！             ")


def verify_session_validity(cl):
    """驗證 session 是否有效"""
    print("\n🔍 正在驗證 session 有效性...")
    
    verification_methods = [
        ("account_info()", lambda: cl.account_info()),
        ("user_info(user_id)", lambda: cl.user_info(cl.user_id)),
        ("检查 sessionid", lambda: bool(getattr(cl, "sessionid", None))),
    ]
    
    success_count = 0
    
    for method_name, method_func in verification_methods:
        try:
            print(f"  • 嘗試 {method_name}...", end="", flush=True)
            result = method_func()
            
            if method_name == "account_info()":
                print(f" ✅")
                print(f"     帳號: {result.username}")
                print(f"     粉絲: {result.follower_count}")
                success_count += 1
            elif method_name == "user_info(user_id)":
                print(f" ✅")
                print(f"     用戶 ID: {result.pk}")
                print(f"     用戶名: {result.username}")
                success_count += 1
            elif result:
                print(f" ✅")
                success_count += 1
        except LoginRequired:
            print(f" ❌ (登入已失效)")
        except json.JSONDecodeError:
            print(f" ⚠️  (JSON 解析失敗，可能是網路問題)")
        except Exception as e:
            error_msg = str(e)[:60]
            print(f" ⚠️  ({error_msg})")
        
        time.sleep(random.uniform(0.5, 1.5))
    
    # 至少有一個驗證方法成功即可
    if success_count >= 1:
        print("\n✅ Session 基本驗證成功！")
        return True
    else:
        print("\n❌ Session 驗證全部失敗")
        return False


def export_sessionid_to_txt(sessionid, export_path):
    """將 sessionid 匯出到 txt 檔案"""
    print(f"\n📝 正在匯出 sessionid 到文件...")
    
    try:
        os.makedirs(os.path.dirname(export_path) or ".", exist_ok=True)
        
        content = f"""IG SessionID 匯出
生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================

SessionID:
{sessionid}

================================================

使用說明:
1. 複製上方的 SessionID
2. 在 Railway 或環境變數中設定 IG_SESSIONID
3. 這樣下次登入會直接使用 sessionid，不需輸入密碼

注意: 請妥善保管此檔案，SessionID 等同於帳號密碼！
"""
        
        with open(export_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        print(f"✅ 已匯出至: {export_path}")
        print(f"\n📋 SessionID 內容:")
        print(sessionid)
        
    except Exception as e:
        print(f"❌ 匯出失敗: {e}")


def main():
    print("\n" + "="*60)
    print("🚀 IG SessionID 強化取得腳本 v2.0")
    print("="*60)
    
    # 載入認證資訊
    username, password, proxy, settings_path = load_credentials()

    if not username or not password:
        print("❌ 缺少 IG_USERNAME 或 IG_PASSWORD。請在環境變數或 config.json 提供。")
        sys.exit(1)

    # 1️⃣  刪除舊的 session 檔案
    delete_old_session_files(settings_path)

    # 2️⃣  初始化客戶端
    print("\n📱 初始化 Instagram 客戶端...")
    cl = Client()

    # 設定 Proxy（可選）
    if proxy:
        try:
            cl.set_proxy(proxy)
            print("🔌 已設定 IG Proxy")
        except Exception as e:
            print(f"⚠️  設定 Proxy 失敗: {e}")

    # 3️⃣  確保目錄存在
    try:
        os.makedirs(os.path.dirname(settings_path), exist_ok=True)
    except Exception:
        pass

    # 4️⃣  登入（帶重試機制）
    print(f"\n🔐 嘗試登入 IG 帳號: {username}")
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            print(f"  嘗試 {attempt}/{max_retries}...", end="", flush=True)
            cl.login(username, password)
            print(" ✅")
            print("✅ Instagram 登入成功")
            break
        except Exception as e:
            print(f" ❌ ({str(e)[:80]})")
            if attempt < max_retries:
                wait_time = random.uniform(5, 10)
                print(f"  ⏳ 等待 {wait_time:.1f} 秒後重試...")
                time.sleep(wait_time)
            else:
                print(f"\n❌ 嘗試 {max_retries} 次後仍然失敗")
                print("\n💡 解決方案：")
                print("  1. 請先在本機 Instagram App 完成一次登入")
                print("  2. 如遇驗證挑戰，於 App 中完成驗證")
                print("  3. 檢查帳號是否被限制登入（檢查郵件）")
                print("  4. 嘗試設定 IG_PROXY 使用代理伺服器")
                print("  5. 等待幾分鐘後再試一次")
                sys.exit(2)

    # 5️⃣  儲存設定
    print(f"\n💾 儲存設定至: {settings_path}")
    try:
        cl.dump_settings(settings_path)
        print("✅ 已儲存設定")
    except Exception as e:
        print(f"⚠️  儲存設定失敗: {e}")

    # 6️⃣  提取 sessionid
    try:
        settings = cl.get_settings()
        sessionid = (
            settings.get("authorization_data", {}).get("sessionid")
            or getattr(cl, "sessionid", None)
        )
        if not sessionid:
            print("⚠️  未能讀取 sessionid，請檢查設定檔或重試。")
            sys.exit(3)
    except Exception as e:
        print(f"❌ 讀取 sessionid 失敗: {e}")
        sys.exit(3)

    # 7️⃣  驗證 session 有效性
    if not verify_session_validity(cl):
        print("⚠️  Session 驗證失敗，但將繼續執行")

    # 8️⃣  進行暖機
    try:
        if not simulate_human_behavior(cl):
            print("⚠️  暖機部分失敗，但將繼續執行")
    except Exception as e:
        print(f"⚠️  暖機異常: {e}")

    # 9️⃣  等待 5-15 分鐘（可選，註解掉以加速測試）
    wait_seconds = random.randint(5*60, 15*60)  # 5-15 分鐘
    wait_with_countdown(wait_seconds)

    # 1️⃣0️⃣  再次驗證 session
    print("\n🔍 第二次驗證 session 有效性...")
    if not verify_session_validity(cl):
        print("⚠️  等待後 session 失效")
        sys.exit(6)

    # 1️⃣1️⃣  匯出 sessionid
    export_path = os.path.join("downloads", "IG_SESSIONID.txt")
    export_sessionid_to_txt(sessionid, export_path)

    print("\n" + "="*60)
    print("✅ 全流程完成！")
    print("="*60)
    print("\n📌 下一步：")
    print(f"  1. 查看 {export_path} 檔案")
    print("  2. 複製 SessionID 值")
    print("  3. 在 Railway 或本地環境變數中設定 IG_SESSIONID")
    print("  4. 後續登入會直接使用 sessionid，無需密碼\n")


if __name__ == "__main__":
    main()
