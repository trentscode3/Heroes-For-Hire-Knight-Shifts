$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

Set-Location $ProjectRoot
$env:KNIGHT_SHIFTS_DEMO = "1"

if (-not (Test-Path $PythonExe)) {
    Write-Host "Demo environment not found. Installing now..."
    powershell -ExecutionPolicy Bypass -File (Join-Path $ProjectRoot "install_windows.ps1")
}

& $PythonExe (Join-Path $ProjectRoot "game_demo.py")
