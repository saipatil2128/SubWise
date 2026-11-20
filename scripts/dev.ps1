# Start the API and the UI in two windows. Run from the repository root:  .\scripts\dev.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$env:PYTHONUTF8 = "1"

$api = "Set-Location '$Root\backend'; & '$Root\backend\.venv\Scripts\Activate.ps1'; " +
       "`$env:PYTHONUTF8='1'; uvicorn subwise.main:app --reload --host 127.0.0.1 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $api

$ui = "Set-Location '$Root\frontend'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $ui

Write-Host "API: http://127.0.0.1:8000/docs   UI: http://localhost:5173"
