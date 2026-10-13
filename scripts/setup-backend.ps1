# BrandShield AI — Backend Setup Script
# Run from the repo root:
#   .\scripts\setup-backend.ps1

Set-Location "$PSScriptRoot\..\backend"

Write-Host "`n🛡  BrandShield AI — Backend Setup" -ForegroundColor Cyan

# 1. Create virtual environment if it doesn't exist
if (-Not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "`n[1/3] Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
} else {
    Write-Host "`n[1/3] Virtual environment already exists." -ForegroundColor Green
}

# 2. Install dependencies
Write-Host "`n[2/3] Installing dependencies..." -ForegroundColor Yellow
& ".venv\Scripts\pip.exe" install -r requirements.txt

# 3. Verify
Write-Host "`n[3/3] Verifying installation..." -ForegroundColor Yellow
& ".venv\Scripts\python.exe" -c "import fastapi, uvicorn, sqlalchemy, alembic, pydantic_settings; print('All core packages OK')"

Write-Host "`n✅  Backend setup complete." -ForegroundColor Green
Write-Host "    To start the server:" -ForegroundColor White
Write-Host "      cd backend" -ForegroundColor Gray
Write-Host "      .venv\Scripts\activate" -ForegroundColor Gray
Write-Host "      uvicorn app.main:app --reload --port 8000" -ForegroundColor Gray
