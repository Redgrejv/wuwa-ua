# Встановлення wuwa-ua на Windows.
# Запуск:  powershell -ExecutionPolicy Bypass -File scripts\install.ps1

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Venv = Join-Path $Root ".venv"
$ConfigDir = Join-Path $env:APPDATA "wuwa-ua"
$DataDir = Join-Path $env:LOCALAPPDATA "wuwa-ua"
$ModelDir = Join-Path $DataDir "models\nllb-1.3b"

function Step($text) { Write-Host "`n==> $text" -ForegroundColor Cyan }
function Warn($text) { Write-Host "    $text" -ForegroundColor Yellow }

Step "Перевірка Python"
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { throw "Python не знайдено. Постав Python 3.12+ з python.org або через winget install Python.Python.3.12" }
$version = (& python -c "import sys; print('%d.%d' % sys.version_info[:2])")
if ([version]$version -lt [version]"3.12") { throw "Потрібен Python 3.12 або новіший, знайдено $version" }
Write-Host "    Python $version"

Step "Tesseract OCR"
$tesseract = Get-Command tesseract -ErrorAction SilentlyContinue
if (-not $tesseract) {
    Warn "Tesseract не знайдено, встановлюю через winget"
    winget install --id UB-Mannheim.TesseractOCR --accept-source-agreements --accept-package-agreements
    Warn "Після встановлення додай теку Tesseract у PATH і перезапусти цей скрипт, якщо команда tesseract досі недоступна"
} else {
    Write-Host "    знайдено: $($tesseract.Source)"
}

Step "Віртуальне середовище"
if (-not (Test-Path $Venv)) { & python -m venv $Venv }
$VenvPython = Join-Path $Venv "Scripts\python.exe"
& $VenvPython -m pip install --quiet --upgrade pip

Step "Залежності"
& $VenvPython -m pip install --quiet -e "$Root[windows]"

Step "Підтримка GPU (необовʼязково, дає прискорення ~5x)"
$hasNvidia = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($hasNvidia) {
    & $VenvPython -m pip install --quiet nvidia-cublas-cu12 nvidia-cudnn-cu12
    Write-Host "    CUDA-бібліотеки встановлено"
} else {
    Warn "NVIDIA GPU не виявлено — переклад працюватиме на процесорі (повільніше)"
}

Step "Модель перекладу (~1.4 ГБ)"
if (Test-Path (Join-Path $ModelDir "model.bin")) {
    Write-Host "    вже завантажена"
} else {
    New-Item -ItemType Directory -Force -Path $ModelDir | Out-Null
    & $VenvPython -c @"
from huggingface_hub import snapshot_download
snapshot_download('JustFrederik/nllb-200-distilled-1.3B-ct2-int8', local_dir=r'$ModelDir')
"@
    $spm = Join-Path $ModelDir "sentencepiece.bpe.model"
    if (-not (Test-Path $spm)) { throw "У моделі бракує sentencepiece.bpe.model" }
}

Step "Конфігурація"
New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null
$ConfigFile = Join-Path $ConfigDir "config.toml"
if (-not (Test-Path $ConfigFile)) {
    Copy-Item (Join-Path $Root "config\config.windows.toml") $ConfigFile
    Write-Host "    створено $ConfigFile"
} else {
    Write-Host "    вже існує, не чіпаю: $ConfigFile"
}
foreach ($name in @("glossary.tsv", "speakers.tsv")) {
    $target = Join-Path $ConfigDir $name
    if (-not (Test-Path $target)) { Copy-Item (Join-Path $Root "config\$name") $target }
}

Step "Ярлик запуску"
$Launcher = Join-Path $Root "wuwa-ua.cmd"
Set-Content -Path $Launcher -Encoding ASCII -Value "@echo off`r`n`"$VenvPython`" -m wuwa_ua.cli %*"
Write-Host "    створено $Launcher"

Write-Host "`nГотово." -ForegroundColor Green
Write-Host "Далі:"
Write-Host "  1. Запусти гру у режимі 'вікно без рамки' (borderless)."
Write-Host "  2. .\wuwa-ua.cmd calibrate --monitor screen   — виділи зону субтитрів мишею."
Write-Host "  3. .\wuwa-ua.cmd run                          — переклад поверх гри."
