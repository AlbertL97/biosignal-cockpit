# =============================================================================
# Yazio export helper
# Reads YAZIO_EMAIL / YAZIO_PASSWORD from the project-root .env file and runs
# the full export (JSON + CSV + SQLite) into data/yazio/.
#
# Usage (from this folder):  .\export.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

# Resolve paths relative to this script
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
$EnvFile     = Join-Path $ProjectRoot ".env"
$OutputDir   = Join-Path $ProjectRoot "data\yazio"
$TokenFile   = Join-Path $ProjectRoot "token.txt"
$Exe         = Join-Path $env:APPDATA "Python\Python314\Scripts\yazio-exporter.exe"

if (-not (Test-Path $Exe)) {
    throw "yazio-exporter not found at $Exe. Run: pip install yazio-exporter"
}
if (-not (Test-Path $EnvFile)) {
    throw "No .env found at $EnvFile. Copy .env.example to .env and fill it in."
}

# Parse .env (KEY=VALUE lines, ignoring comments/blanks)
$cfg = @{}
foreach ($line in Get-Content $EnvFile) {
    if ($line -match '^\s*#' -or $line -match '^\s*$') { continue }
    $kv = $line -split '=', 2
    if ($kv.Count -eq 2) { $cfg[$kv[0].Trim()] = $kv[1].Trim() }
}

$email    = $cfg['YAZIO_EMAIL']
$password = $cfg['YAZIO_PASSWORD']
if (-not $email -or -not $password) {
    throw "YAZIO_EMAIL / YAZIO_PASSWORD missing from .env"
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

Write-Host "Logging in to Yazio..." -ForegroundColor Cyan
& $Exe login $email $password -o $TokenFile

foreach ($fmt in @('json', 'csv', 'sqlite')) {
    Write-Host "Exporting all data ($fmt)..." -ForegroundColor Cyan
    & $Exe export-all $email $password -o $OutputDir --format $fmt
}

Write-Host "Done. Output in: $OutputDir" -ForegroundColor Green
