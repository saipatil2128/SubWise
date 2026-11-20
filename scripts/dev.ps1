# Start the API and the UI in two PowerShell windows. Run from the repository root:  .\scripts\dev.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$env:PYTHONUTF8 = "1"

if (-not (Test-Path "$Root\backend\.venv\Scripts\python.exe")) {
    throw "backend\.venv not found. Run .\scripts\setup.ps1 first."
}

# Ollama is optional: without it SubWise uses rule-based parsing and template reports.
try {
    Invoke-RestMethod -Uri "http://localhost:11434/api/version" -TimeoutSec 2 | Out-Null
    Write-Host "Ollama is running."
} catch {
    Write-Warning "Ollama is not reachable on http://localhost:11434. Start the Ollama app (or run 'ollama serve') for AI features."
}

$api = "Set-Location '$Root\backend'; `$env:PYTHONUTF8='1'; " +
       "& '.\.venv\Scripts\python.exe' -m uvicorn subwise.main:create_app --factory --reload --host 127.0.0.1 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $api

$ui = "Set-Location '$Root\frontend'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $ui

Write-Host "UI:  http://localhost:5173"
Write-Host "API: http://127.0.0.1:8000/docs"
