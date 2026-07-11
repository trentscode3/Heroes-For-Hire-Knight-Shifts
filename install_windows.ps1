param(
    [string]$Python = "py"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPath = Join-Path $ProjectRoot ".venv"
$PythonExe = Join-Path $VenvPath "Scripts\python.exe"

Set-Location $ProjectRoot

if (-not (Get-Command $Python -ErrorAction SilentlyContinue)) {
    Write-Host "Python was not found."
    Write-Host "Install Python 3.11+ from https://www.python.org/downloads/"
    Write-Host "During install, enable: Add python.exe to PATH"
    exit 1
}

if (-not (Test-Path $PythonExe)) {
    & $Python -m venv $VenvPath
}

& $PythonExe -m pip install --upgrade pip
& $PythonExe -m pip install -r (Join-Path $ProjectRoot "requirements.txt")

Write-Host ""
Write-Host "Install complete. Run the demo with:"
Write-Host "powershell -ExecutionPolicy Bypass -File .\run_demo.ps1"
