# BrandShield AI — Start PostgreSQL via Docker Compose
# Run from the repo root:
#   .\scripts\start-db.ps1
#
# Requires Docker Desktop running.

Set-Location "$PSScriptRoot\.."

Write-Host "`n🛡  Starting BrandShield AI PostgreSQL..." -ForegroundColor Cyan

docker-compose up -d postgres

Write-Host "`nWaiting for PostgreSQL to be healthy..."
Start-Sleep -Seconds 3
docker-compose ps postgres

Write-Host "`n✅  PostgreSQL is running at localhost:5432" -ForegroundColor Green
Write-Host "    DB:   brandshield" -ForegroundColor Gray
Write-Host "    User: brandshield" -ForegroundColor Gray
