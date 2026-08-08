# Offline install from local wheels folder.
# Usage (from project root):
#   python -m venv .venv
#   .\.venv\Scripts\activate
#   .\scripts\install_from_wheels.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$WheelsDir = Join-Path $ProjectRoot "wheels"
$Requirements = Join-Path $ProjectRoot "requirements-wheels.txt"
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    $Python = "python"
}

if (-not (Test-Path $WheelsDir)) {
    throw "Missing wheels folder. Copy wheels from USB or run .\scripts\download_wheels.ps1 on a PC with internet."
}

$wheelCount = (Get-ChildItem $WheelsDir -Filter "*.whl").Count
if ($wheelCount -eq 0) {
    throw "No .whl files found in wheels folder. Copy wheels from USB first."
}

Write-Host "Installing from $wheelCount local wheel(s) (offline, no internet) ..."
& $Python -m pip install --no-index --find-links $WheelsDir -r $Requirements

Write-Host "Installed from local wheels."