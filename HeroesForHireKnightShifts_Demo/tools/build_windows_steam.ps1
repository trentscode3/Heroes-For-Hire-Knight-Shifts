param(
    [string]$Python = "py",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$VenvPath = Join-Path $ProjectRoot ".venv-build"
$PythonExe = Join-Path $VenvPath "Scripts\python.exe"
$DistPath = Join-Path $ProjectRoot "dist\HeroesForHireKnightShifts"
$SpecPath = Join-Path $ProjectRoot "HeroesForHireKnightShifts.spec"

Set-Location $ProjectRoot

if (-not (Test-Path $PythonExe)) {
    & $Python -m venv $VenvPath
}

if (-not $SkipInstall) {
    & $PythonExe -m pip install --upgrade pip
    & $PythonExe -m pip install -r (Join-Path $ProjectRoot "requirements-build.txt")
}

& $PythonExe -m compileall -q .
& $PythonExe -m PyInstaller --clean --noconfirm $SpecPath

if (-not (Test-Path (Join-Path $DistPath "HeroesForHireKnightShifts.exe"))) {
    throw "Build failed: executable was not created."
}

Write-Host ""
Write-Host "Steam-ready Windows folder:"
Write-Host $DistPath
Write-Host ""
Write-Host "Upload every file in that folder to SteamPipe."
