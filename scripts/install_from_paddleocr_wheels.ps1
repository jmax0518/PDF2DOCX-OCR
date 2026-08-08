# Offline install for optional PaddleOCR stack.
# Usage (from project root, after core packages are installed):
#   .\.venv\Scripts\activate
#   .\scripts\install_from_paddleocr_wheels.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$CoreWheelsDir = Join-Path $ProjectRoot "wheels"
$PaddleWheelsDir = Join-Path $ProjectRoot "wheels\paddleocr"
$Requirements = Join-Path $ProjectRoot "requirements-paddleocr-wheels.txt"
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    $Python = "python"
}

if (-not (Test-Path $PaddleWheelsDir)) {
    throw "Missing wheels\paddleocr folder. Copy from USB or run .\scripts\download_wheels.ps1 -IncludePaddleOCR on a PC with internet."
}

$wheelCount = (Get-ChildItem $PaddleWheelsDir -Filter "*.whl").Count
if ($wheelCount -eq 0) {
    throw "No .whl files found in wheels\paddleocr. Copy PaddleOCR wheels from USB first."
}

Write-Host "Installing PaddleOCR from $wheelCount local wheel(s) (offline) ..."
& $Python -m pip install --no-index --find-links $CoreWheelsDir --find-links $PaddleWheelsDir -r $Requirements

Write-Host "PaddleOCR installed from local wheels."
