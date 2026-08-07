# Download offline install bundle: core wheels + PaddleOCR wheels + PaddleX models.
# Run on a PC with internet (from project root):
#   .\scripts\download_offline_bundle.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$WheelsDir = Join-Path $ProjectRoot "wheels"
$PaddleWheelsDir = Join-Path $WheelsDir "paddleocr"
$ModelsDir = Join-Path $ProjectRoot "offline_models"
$CoreReq = Join-Path $ProjectRoot "requirements-wheels.txt"
$PaddleReq = Join-Path $ProjectRoot "requirements-paddleocr-wheels.txt"
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

New-Item -ItemType Directory -Force -Path $WheelsDir | Out-Null
New-Item -ItemType Directory -Force -Path $PaddleWheelsDir | Out-Null
New-Item -ItemType Directory -Force -Path $ModelsDir | Out-Null

Write-Host "=== 1) Core wheels -> $WheelsDir ==="
& $Python -m pip download -r $CoreReq -d $WheelsDir --timeout 600 --retries 10
if ($LASTEXITCODE -ne 0) { throw "Core wheel download failed" }

# langdetect is often sdist-only; ensure a wheel exists
& $Python -m pip wheel "langdetect==1.0.9" -w $WheelsDir --no-deps
if ($LASTEXITCODE -ne 0) { throw "langdetect wheel build failed" }

Write-Host "=== 2) PaddleOCR / PaddleX wheels -> $PaddleWheelsDir ==="
& $Python -m pip download -r $PaddleReq -d $PaddleWheelsDir --timeout 600 --retries 10
if ($LASTEXITCODE -ne 0) { throw "Paddle wheel download failed" }

Write-Host "=== 3) Copy PaddleX official models -> $ModelsDir ==="
$SrcModels = Join-Path $env:USERPROFILE ".paddlex\official_models"
if (-not (Test-Path $SrcModels)) {
    Write-Host "WARNING: No models at $SrcModels"
    Write-Host "Run one exact/structure conversion first to download models, then re-run this script."
} else {
    $DestModels = Join-Path $ModelsDir "official_models"
    if (Test-Path $DestModels) { Remove-Item $DestModels -Recurse -Force }
    Copy-Item $SrcModels $DestModels -Recurse -Force
}

Write-Host ""
Write-Host "=== Bundle summary ==="
$core = Get-ChildItem $WheelsDir -Filter "*.whl" -File
$paddle = Get-ChildItem $PaddleWheelsDir -Filter "*.whl" -File -ErrorAction SilentlyContinue
$coreSum = ($core | Measure-Object Length -Sum).Sum
$paddleSum = ($paddle | Measure-Object Length -Sum).Sum
Write-Host ("Core wheels:   {0} files, {1:N1} MB" -f $core.Count, ($coreSum/1MB))
Write-Host ("Paddle wheels: {0} files, {1:N1} MB" -f $paddle.Count, ($paddleSum/1MB))
if (Test-Path (Join-Path $ModelsDir "official_models")) {
    $m = Get-ChildItem (Join-Path $ModelsDir "official_models") -Recurse -File | Measure-Object Length -Sum
    Write-Host ("Models:        {0} files, {1:N1} MB" -f $m.Count, ($m.Sum/1MB))
}
Write-Host ("Total approx:  {0:N1} MB" -f (($coreSum + $paddleSum + $(if($m){$m.Sum}else{0}))/1MB))
Write-Host ""
Write-Host "Copy to USB: wheels\  +  offline_models\  +  requirements-*.txt  +  project source"
Write-Host "On offline PC see: offline_models\INSTALL_OFFLINE.txt"
