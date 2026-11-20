# Run every check CI runs. From the repository root:  .\scripts\test.ps1
#   -E2E    also run the browser end-to-end test (needs: pip install -e "backend[browser]" and
#           python -m playwright install chromium)
param([switch]$E2E)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$env:PYTHONUTF8 = "1"
$py = "$Root\backend\.venv\Scripts\python.exe"

Push-Location "$Root\backend"
& $py -m ruff check .;          if ($LASTEXITCODE) { throw "ruff check failed" }
& $py -m ruff format --check .; if ($LASTEXITCODE) { throw "ruff format failed" }
& $py -m mypy;                  if ($LASTEXITCODE) { throw "mypy failed" }
& $py -m pytest;                if ($LASTEXITCODE) { throw "pytest failed" }
Pop-Location

Push-Location "$Root\frontend"
npm run typecheck;     if ($LASTEXITCODE) { throw "typecheck failed" }
npm test;              if ($LASTEXITCODE) { throw "vitest failed" }
npm run build;         if ($LASTEXITCODE) { throw "build failed" }
Pop-Location

if ($E2E) {
    Push-Location "$Root\backend"
    & $py -m pytest -m e2e;     if ($LASTEXITCODE) { throw "browser E2E failed" }
    Pop-Location
}

Write-Host "`nAll checks passed."
