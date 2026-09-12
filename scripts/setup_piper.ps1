$ErrorActionPreference = 'Stop'

Write-Host "MIRA - Free Hindi Female Voice setup" -ForegroundColor Cyan

$python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "Virtual environment not found. Create .venv first." -ForegroundColor Yellow
    exit 1
}

& $python -m pip install --upgrade pip
& $python -m pip install "piper-tts>=1.2.0"

$modelDir = "models\piper"
New-Item -ItemType Directory -Force -Path $modelDir | Out-Null

Write-Host "Downloading Hindi voice: hi_IN-priyamvada-medium ..." -ForegroundColor Cyan
& $python -m piper.download_voices --download-dir $modelDir hi_IN-priyamvada-medium

$source = Join-Path $modelDir "hi_IN-priyamvada-medium.onnx"
if (-not (Test-Path $source)) {
    Write-Host "Voice model was not downloaded." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

Write-Host "Piper voice installed successfully." -ForegroundColor Green
Write-Host "Restart MIRA server, then enable Voice ON in the UI." -ForegroundColor Green
