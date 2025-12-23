# Export environment variables to Railway CLI commands (safe: reads local config without committing secrets)
# Usage: Run in PowerShell from project root
#   pwsh -File scripts/export_to_railway.ps1
# It will print commands. Review and run them manually.

param(
    [string]$ConfigPath = "config.json",
    [string]$IgSettingsPath = "downloads/instagrapi_settings.json"
)

function Read-JsonFile([string]$path) {
    if (Test-Path $path) {
        try {
            $raw = Get-Content -Path $path -Raw -ErrorAction Stop
            return $raw | ConvertFrom-Json
        } catch {
            Write-Host "⚠️ 無法讀取 JSON: $path" -ForegroundColor Yellow
            return $null
        }
    }
    return $null
}

function Minify-Json([string]$path) {
    if (Test-Path $path) {
        try {
            $raw = Get-Content -Path $path -Raw -ErrorAction Stop
            $obj = $raw | ConvertFrom-Json
            # Re-emit compact JSON
            return ($obj | ConvertTo-Json -Compress)
        } catch {
            Write-Host "⚠️ 無法壓縮 JSON: $path" -ForegroundColor Yellow
        }
    }
    return ""
}

$cfg = Read-JsonFile $ConfigPath
$settingsJson = Minify-Json $IgSettingsPath

Write-Host "=== 生成 Railway 變數設定指令（請先安裝 @railway/cli） ===" -ForegroundColor Cyan
Write-Host "# 安裝 CLI" -ForegroundColor DarkGray
Write-Host "npm i -g @railway/cli" -ForegroundColor DarkGray
Write-Host "railway login" -ForegroundColor DarkGray
Write-Host "railway link" -ForegroundColor DarkGray

function Print-Var([string]$key, [string]$val) {
    if (-not [string]::IsNullOrWhiteSpace($val)) {
        # Escape quotes for PowerShell
        $escaped = $val.Replace('"','\"')
        Write-Host "railway variables set $key \"$escaped\""
    }
}

# OpenAI / Facebook
Print-Var "API_KEY" $cfg.API_KEY
Print-Var "FB_TOKEN" $cfg.FB_TOKEN

# Instagram
Print-Var "IG_USERNAME" $cfg.IG_USERNAME
Print-Var "IG_PASSWORD" $cfg.IG_PASSWORD
# Prefer sessionid when available (paste manually if not in config)
Print-Var "IG_SESSIONID" $cfg.IG_SESSIONID

# Settings JSON
if (-not [string]::IsNullOrWhiteSpace($settingsJson)) {
    Print-Var "IG_SETTINGS_JSON" $settingsJson
}
# Settings PATH (optional persistent path)
Print-Var "IG_SETTINGS_PATH" "downloads/instagrapi_settings.json"

# Proxy (optional)
Print-Var "IG_PROXY" $cfg.IG_PROXY

# App config
Print-Var "NEWS" $cfg.NEWS
Print-Var "MODE" $cfg.MODE
Print-Var "POST_DELAY_MIN" ([string]$cfg.POST_DELAY_MIN)
Print-Var "POST_DELAY_MAX" ([string]$cfg.POST_DELAY_MAX)
Print-Var "POST_TO_FACEBOOK" ([string]$cfg.POST_TO_FACEBOOK)
Print-Var "POST_TO_INSTAGRAM" ([string]$cfg.POST_TO_INSTAGRAM)

Write-Host "\n# 執行以上指令以設定 Railway 環境變數。" -ForegroundColor Green
Write-Host "# 注意：不要將真實機密（config.json, .env, settings.json）提交到 GitHub。" -ForegroundColor Yellow
