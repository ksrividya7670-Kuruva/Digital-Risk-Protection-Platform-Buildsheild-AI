# BrandShield AI — Frontend Setup Script
# Run from the repo root:
#   .\scripts\setup-frontend.ps1
#
# Requires Node.js 18+ installed and in PATH.
# Download from: https://nodejs.org

Set-Location "$PSScriptRoot\..\frontend"

Write-Host "`n🛡  BrandShield AI — Frontend Setup" -ForegroundColor Cyan

# Check Node
try {
    $nodeVersion = & "C:\Program Files\nodejs\node.exe" --version
    Write-Host "`n  Node.js: $nodeVersion" -ForegroundColor Green
} catch {
    # Try PATH-resolved node
    try {
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")
        $nodeVersion = node --version
        Write-Host "`n  Node.js: $nodeVersion" -ForegroundColor Green
    } catch {
        Write-Host "`n❌  Node.js not found. Install from https://nodejs.org" -ForegroundColor Red
        exit 1
    }
}

# Install dependencies
Write-Host "`n[1/1] Installing npm dependencies..." -ForegroundColor Yellow
# Use npm.cmd directly to avoid PowerShell execution policy issues with npm.ps1
$npmCmd = "C:\Program Files\nodejs\npm.cmd"
if (-Not (Test-Path $npmCmd)) {
    # Fallback to PATH-resolved npm.cmd
    $npmCmd = "npm.cmd"
}
& $npmCmd install

Write-Host "`n✅  Frontend setup complete." -ForegroundColor Green
Write-Host "    To start the dev server:" -ForegroundColor White
Write-Host "      cd frontend" -ForegroundColor Gray
Write-Host "      npm run dev" -ForegroundColor Gray
