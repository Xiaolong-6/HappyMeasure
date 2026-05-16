$ErrorActionPreference = "Stop"

# Space-safe launcher: all paths are resolved from this script and passed with LiteralPath / call operator.
$ProjectDir = Split-Path -Parent $PSCommandPath
Set-Location -LiteralPath $ProjectDir
$env:PYTHONPATH = (Join-Path $ProjectDir "src") + ";" + $env:PYTHONPATH
$VenvPy = Join-Path $ProjectDir ".venv\Scripts\python.exe"

Write-Host "HappyMeasure offline alpha launcher"
Write-Host "Working directory: $ProjectDir"

if ((Test-Path -LiteralPath (Join-Path $ProjectDir ".venv")) -and (-not (Test-Path -LiteralPath $VenvPy))) {
    Write-Host "Existing .venv is incomplete or broken. Recreating it..."
    Remove-Item -LiteralPath (Join-Path $ProjectDir ".venv") -Recurse -Force
}

if (-not (Test-Path -LiteralPath $VenvPy)) {
    Write-Host "Creating local virtual environment..."
    python -m venv (Join-Path $ProjectDir ".venv")
}

if (-not (Test-Path -LiteralPath $VenvPy)) {
    throw ".venv\Scripts\python.exe was not created."
}

# A copied/synced venv can keep an absolute reference to another Windows user
# profile, e.g. C:\Users\carll\... . The python.exe file may exist but cannot
# start. Validate it before launch and rebuild if stale.
& $VenvPy -c "import sys; print(sys.executable)" *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Existing .venv is stale or points to a missing base Python. Recreating it..."
    Remove-Item -LiteralPath (Join-Path $ProjectDir ".venv") -Recurse -Force -ErrorAction SilentlyContinue
    python -m venv (Join-Path $ProjectDir ".venv")
    if (-not (Test-Path -LiteralPath $VenvPy)) {
        throw ".venv\Scripts\python.exe was not recreated."
    }
}

Write-Host "Installing/updating local package..."
& $VenvPy -m pip install -e $ProjectDir

Write-Host "Launching HappyMeasure..."
& $VenvPy -m happymeasure
if ($LASTEXITCODE -ne 0) {
    Write-Host "Public happymeasure entry failed. Trying legacy keith_ivt entry..."
    & $VenvPy -m keith_ivt
}
Read-Host "Press Enter to close"
