# Download all Python wheels for offline setup (Windows, Python 3.10+).
# Usage (from project root):
#   .\scripts\download_wheels.ps1
#   .\scripts\download_wheels.ps1 -IncludePaddleOCR

param(
    [switch]$IncludePaddleOCR
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$WheelsDir = Join-Path $ProjectRoot "wheels"
$Requirements = Join-Path $ProjectRoot "requirements-wheels.txt"
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    $Python = "python"
}

New-Item -ItemType Directory -Force -Path $WheelsDir | Out-Null

function Download-Package {
    param(
        [string]$Package,
        [switch]$AllowSource
    )

    Write-Host "Downloading $Package ..."
    $args = @(
        "-m", "pip", "download",
        $Package,
        "-d", $WheelsDir,
        "--timeout", "600",
        "--retries", "10"
    )
    if (-not $AllowSource) {
        $args += "--only-binary=:all:"
    }

    & $Python @args
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to download $Package"
    }
}

Get-Content $Requirements | ForEach-Object {
    $line = $_.Trim()
    if ($line -eq "" -or $line.StartsWith("#")) {
        return
    }
    $package = ($line -split "#")[0].Trim()
    if ($package -eq "langdetect==1.0.9") {
        Download-Package -Package $package -AllowSource
    } else {
        Download-Package -Package $package
    }
}

# langdetect ships as sdist only; build a wheel for offline install.
Write-Host "Building langdetect wheel ..."
& $Python -m pip wheel "langdetect==1.0.9" -w $WheelsDir --no-deps
if ($LASTEXITCODE -ne 0) {
    throw "Failed to build langdetect wheel"
}

if ($IncludePaddleOCR) {
    $PaddleWheelsDir = Join-Path $WheelsDir "paddleocr"
    New-Item -ItemType Directory -Force -Path $PaddleWheelsDir | Out-Null
    Write-Host "Downloading optional PaddleOCR stack (large, ~200 MB) ..."
    & $Python -m pip download "paddlepaddle==3.3.1" "paddleocr==3.7.0" -d $PaddleWheelsDir --timeout 600 --retries 10
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to download PaddleOCR packages"
    }
    Write-Host "PaddleOCR wheels saved to: $PaddleWheelsDir"
}

Write-Host ""
Write-Host "Done. Core wheels: $WheelsDir"
Get-ChildItem $WheelsDir -Filter "*.whl" | Select-Object Name, @{Name="MB";Expression={[math]::Round($_.Length/1MB,2)}}
if ($IncludePaddleOCR) {
    Get-ChildItem (Join-Path $WheelsDir "paddleocr") -Filter "*.whl" | Measure-Object -Property Length -Sum | ForEach-Object {
        Write-Host "PaddleOCR wheels: $($_.Count) files, $([math]::Round($_.Sum/1MB,1)) MB"
    }
}
