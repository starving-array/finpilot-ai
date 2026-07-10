$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Failed = $false

Write-Host "`n========== FHSS — RUNNING ALL TESTS ==========`n" -ForegroundColor Cyan

# 1. Backend (scoring module)
Write-Host "--- Backend (scoring) ---" -ForegroundColor Yellow
Push-Location (Join-Path $Root "backend")
try {
    ./mvnw.cmd test -pl scoring -am -q
    if ($LASTEXITCODE -eq 0) { Write-Host "  PASSED" -ForegroundColor Green }
    else { $Failed = $true; Write-Host "  FAILED" -ForegroundColor Red }
} finally { Pop-Location }

# 2. ML Service
Write-Host "`n--- ML Service ---" -ForegroundColor Yellow
Push-Location (Join-Path $Root "ml-service")
try {
    python -m pytest tests/ -v --tb=short
    if ($LASTEXITCODE -eq 0) { Write-Host "`n  PASSED" -ForegroundColor Green }
    else { $Failed = $true; Write-Host "`n  FAILED" -ForegroundColor Red }
} finally { Pop-Location }

# 3. Frontend
Write-Host "`n--- Frontend ---" -ForegroundColor Yellow
Push-Location (Join-Path $Root "frontend")
try {
    npx vitest run --reporter=verbose
    if ($LASTEXITCODE -eq 0) { Write-Host "`n  PASSED" -ForegroundColor Green }
    else { $Failed = $true; Write-Host "`n  FAILED" -ForegroundColor Red }
} finally { Pop-Location }

# 4. CLI
Write-Host "`n--- CLI ---" -ForegroundColor Yellow
Push-Location $Root
try {
    python -m pytest tests/test_cli.py -v --tb=short
    if ($LASTEXITCODE -eq 0) { Write-Host "`n  PASSED" -ForegroundColor Green }
    else { $Failed = $true; Write-Host "`n  FAILED" -ForegroundColor Red }
} finally { Pop-Location }

Write-Host "`n============================================" -ForegroundColor Cyan
if ($Failed) { Write-Host "SOME TESTS FAILED" -ForegroundColor Red; exit 1 }
else { Write-Host "ALL TESTS PASSED" -ForegroundColor Green; exit 0 }
