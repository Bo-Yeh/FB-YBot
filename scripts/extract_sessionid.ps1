# 從本機 instagrapi settings 檔案中提取 sessionid
# Usage: pwsh -File scripts/extract_sessionid.ps1

param(
    [string]$SettingsPath = "downloads/instagrapi_settings.json"
)

if (-not (Test-Path $SettingsPath)) {
    Write-Host "❌ 找不到設定檔: $SettingsPath" -ForegroundColor Red
    Write-Host "請先在本機執行一次 autopost.py 以完成 IG 登入與驗證" -ForegroundColor Yellow
    exit 1
}

try {
    $settings = Get-Content -Path $SettingsPath -Raw | ConvertFrom-Json
    $sessionid = $settings.authorization_data.sessionid
    
    if ([string]::IsNullOrWhiteSpace($sessionid)) {
        Write-Host "⚠️ 設定檔中未找到 sessionid" -ForegroundColor Yellow
        exit 1
    }
    
    Write-Host "`n✅ 已提取 sessionid：" -ForegroundColor Green
    Write-Host $sessionid -ForegroundColor Cyan
    
    Write-Host "`n📋 複製以下指令並在 Railway 專案中執行：" -ForegroundColor Yellow
    Write-Host "railway variables set IG_SESSIONID `"$sessionid`"" -ForegroundColor White
    
    Write-Host "`n💡 提示：" -ForegroundColor Cyan
    Write-Host "- 使用 IG_SESSIONID 比完整 JSON 更穩定且容易設定"
    Write-Host "- Railway 會自動在登入後儲存新 settings"
    Write-Host "- 若 sessionid 過期，重新在本機登入後再次執行此腳本"
    
} catch {
    Write-Host "❌ 解析設定檔失敗: $_" -ForegroundColor Red
    exit 1
}
