# =============================================================================
# Health Intelligence — local launcher
# Starts the FastAPI backend (port 8000) and the Vite frontend (port 5173),
# then opens the cockpit in your browser.
#
# Usage:  .\run.ps1        (Ctrl+C in each window to stop)
# =============================================================================

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

# Optional: enable LIVE PubMed lookups by setting your email for NCBI E-utilities.
# Without it, the evidence layer falls back to the curated guideline references.
# $env:ENTREZ_EMAIL = "you@example.com"

Write-Host "Starting backend (http://127.0.0.1:8000) ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
  "-NoExit", "-Command",
  "cd '$Root\backend'; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
)

Start-Sleep -Seconds 2
Write-Host "Starting frontend (http://localhost:5173) ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
  "-NoExit", "-Command",
  "cd '$Root\frontend'; npm run dev"
)

Start-Sleep -Seconds 3
Start-Process "http://localhost:5173/"
Write-Host "Cockpit opening at http://localhost:5173/  (API docs: http://127.0.0.1:8000/docs)" -ForegroundColor Green
