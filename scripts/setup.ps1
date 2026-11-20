# One-time setup for SubWise on Windows. Run from the repository root:  .\scripts\setup.ps1
#   -Browser   also install Playwright + Chromium (JS-rendered pricing pages and the E2E test)
param([switch]$Browser)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Need($cmd, $hint) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { throw "$cmd not found. $hint" }
}
Need "py" "Install Python 3.12:  winget install -e --id Python.Python.3.12   (then open a new terminal)"
Need "npm" "Install Node.js 22 LTS:  winget install -e --id OpenJS.NodeJS.LTS   (then open a new terminal)"

$env:PYTHONUTF8 = "1"   # print the rupee sign correctly in the Windows console

if (-not (Test-Path "backend\.venv")) {
    Write-Host "Creating backend\.venv with Python 3.12..."
    py -3.12 -m venv backend\.venv
}
$py = "backend\.venv\Scripts\python.exe"
& $py -m pip install --upgrade pip
$extras = if ($Browser) { "backend[dev,browser]" } else { "backend[dev]" }
& $py -m pip install -e $extras
if ($Browser) { & $py -m playwright install chromium }

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    # Generate a random JWT secret so no shared default is ever used.
    $secret = [Convert]::ToBase64String((1..48 | ForEach-Object { Get-Random -Maximum 256 }) -as [byte[]])
    (Get-Content ".env") -replace "^SUBWISE_JWT_SECRET=.*", "SUBWISE_JWT_SECRET=$secret" | Set-Content ".env" -Encoding utf8
    Write-Host "Created .env with a random SUBWISE_JWT_SECRET."
}

Push-Location backend
& ".\.venv\Scripts\python.exe" -m subwise.cli init-db
Pop-Location

Push-Location frontend
npm ci
Pop-Location

if (Get-Command "ollama" -ErrorAction SilentlyContinue) {
    Write-Host "Pulling qwen2.5:3b (about 1.9 GB, first time only)..."
    ollama pull qwen2.5:3b
} else {
    Write-Warning "Ollama not found. Install it for AI features:  winget install -e --id Ollama.Ollama   then:  ollama pull qwen2.5:3b"
}

& $py backend\scripts\check_env.py
Write-Host "`nSetup finished. Start everything with: .\scripts\dev.ps1  (or VS Code: Run and Debug > 'SubWise: backend + frontend')"
