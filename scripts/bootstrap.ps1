# Одна команда для встановлення wuwa-ua на Windows:
#
#   irm https://raw.githubusercontent.com/Redgrejv/wuwa-ua/master/scripts/bootstrap.ps1 | iex
#
# Скрипт самодостатній: клонує репозиторій у %LOCALAPPDATA%\Programs\wuwa-ua
# і запускає встановлення. Повторний запуск оновлює наявну копію.

$ErrorActionPreference = "Stop"

$Repo = "https://github.com/Redgrejv/wuwa-ua.git"
$Target = Join-Path $env:LOCALAPPDATA "Programs\wuwa-ua"

function Step($text) { Write-Host "`n==> $text" -ForegroundColor Cyan }

Step "Перевірка git"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "    git не знайдено, встановлюю" -ForegroundColor Yellow
    winget install --id Git.Git --accept-source-agreements --accept-package-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
}

Step "Вихідний код"
if (Test-Path (Join-Path $Target ".git")) {
    Write-Host "    вже склоновано, оновлюю"
    git -C $Target pull --ff-only
} else {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Target) | Out-Null
    git clone $Repo $Target
}

Step "Встановлення"
& powershell -ExecutionPolicy Bypass -File (Join-Path $Target "scripts\install.ps1")

Write-Host "`nВстановлено в $Target" -ForegroundColor Green
Write-Host "Запуск:  cd `"$Target`"; .\wuwa-ua.cmd run"
