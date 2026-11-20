# One-time setup for SubWise on Windows. Run from the repository root:  .\scripts\setup.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Need($cmd, $hint) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { throw "$cmd not found. $hint" }
}
Need "py" "Install Python 3.12 from python.org (includes the 'py' launcher)."
Need "npm" "Install Node.js 22 LTS from nodejs.org."

$env:PYTHONUTF8 = "1"   # print the rupee sign correctly in the Windows console

if (-not (Test-Path "backend\.venv")) {
    Write-Host "Creating backend\.venv with Python 3.12..."
    py -3.12 -m venv backend\.venv
}
& backend\.venv\Scripts\python.exe -m pip install --upgrade pip
& backend\.venv\Scripts\python.exe -m pip install -e "backend[dev]"

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example - set SUBWISE_JWT_SECRET before sharing the app."
}

Push-Location frontend
npm ci
Pop-Location

& backend\.venv\Scripts\python.exe backend\scripts\check_env.py
Write-Host "`nSetup finished. Start everything with: .\scripts\dev.ps1"
