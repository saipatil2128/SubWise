# Run every check CI runs. From the repository root:  .\scripts\test.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$env:PYTHONUTF8 = "1"

Push-Location "$Root\backend"
& .\.venv\Scripts\Activate.ps1
ruff check .;          if ($LASTEXITCODE) { throw "ruff check failed" }
ruff format --check .; if ($LASTEXITCODE) { throw "ruff format failed" }
mypy;                  if ($LASTEXITCODE) { throw "mypy failed" }
pytest;                if ($LASTEXITCODE) { throw "pytest failed" }
Pop-Location

Push-Location "$Root\frontend"
npm run typecheck;     if ($LASTEXITCODE) { throw "typecheck failed" }
npm test;              if ($LASTEXITCODE) { throw "vitest failed" }
npm run build;         if ($LASTEXITCODE) { throw "build failed" }
Pop-Location

Write-Host "`nAll checks passed."
