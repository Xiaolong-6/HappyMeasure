$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location -LiteralPath $ProjectRoot

$LogDir = Join-Path $ProjectRoot "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$BuildLog = Join-Path $LogDir "build_portable_windows_app.log"

function Write-Step([string]$Message) {
    Write-Host $Message
    Add-Content -LiteralPath $BuildLog -Value $Message
}

function Test-Python314([string]$Command, [string[]]$Args = @()) {
    try {
        & $Command @Args -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,14) else 1)" *> $null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Pick-Python314 {
    if (Test-Python314 "py" @("-3.14")) {
        return @("py", "-3.14")
    }
    if (Test-Python314 "python") {
        return @("python")
    }
    throw "Python 3.14 was not found. Install Python 3.14 or make sure 'py -3.14' works."
}

Write-Step "=========================================="
Write-Step "Building HappyMeasure portable Windows app with Python 3.14"
Write-Step "Working directory: $ProjectRoot"
Write-Step "=========================================="

Remove-Item -Recurse -Force -LiteralPath "build" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force -LiteralPath "dist" -ErrorAction SilentlyContinue

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $VenvPython) {
    & $VenvPython -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,14) else 1)" *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Step "Existing .venv is missing, broken, or not Python 3.14; deleting .venv"
        Remove-Item -Recurse -Force -LiteralPath ".venv"
    }
}

if (-not (Test-Path -LiteralPath $VenvPython)) {
    $PythonCmd = Pick-Python314
    Write-Step "Creating build virtual environment with $($PythonCmd -join ' ')"
    & $PythonCmd[0] @($PythonCmd[1..($PythonCmd.Count-1)] | Where-Object { $_ }) -m venv .venv
}

& ".\.venv\Scripts\Activate.ps1"
python -c "import sys; print('Build Python:', sys.version.replace(chr(10), ' ')); print('Executable:', sys.executable); raise SystemExit(0 if sys.version_info[:2] == (3,14) else 1)"

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pip install --upgrade pyinstaller

Write-Step "Running Python 3.14 smoke check..."
python -c "import keith_ivt; from keith_ivt.ui.simple_app import main; import matplotlib; import serial; print('Smoke check OK')"

Write-Step "Skipping full pytest validation for Python 3.14 build. Run simulator + hardware preflight manually after packaging."

Write-Step "Running PyInstaller..."
Push-Location packaging
pyinstaller --noconfirm --clean HappyMeasure.spec
Pop-Location

if (-not (Test-Path -LiteralPath "dist\HappyMeasure\HappyMeasure.exe")) {
    throw "dist\HappyMeasure\HappyMeasure.exe was not created."
}

New-Item -ItemType Directory -Force -Path "dist\HappyMeasure\logs" | Out-Null
New-Item -ItemType Directory -Force -Path "dist\HappyMeasure\examples" | Out-Null
Copy-Item -Force "packaging\README_FIRST_PORTABLE.txt" "dist\HappyMeasure\README_FIRST.txt" -ErrorAction SilentlyContinue
Copy-Item -Force "docs\HARDWARE_VALIDATION_PROTOCOL.md" "dist\HappyMeasure\HARDWARE_VALIDATION_PROTOCOL.md" -ErrorAction SilentlyContinue
Copy-Item -Force "docs\HARDWARE_DRY_RUN_GUIDE.md" "dist\HappyMeasure\HARDWARE_DRY_RUN_GUIDE.md" -ErrorAction SilentlyContinue

Write-Step "=========================================="
Write-Step "Build finished."
Write-Step "Portable app folder: $ProjectRoot\dist\HappyMeasure"
Write-Step "Main executable: $ProjectRoot\dist\HappyMeasure\HappyMeasure.exe"
Write-Step "=========================================="
Write-Step "Next step: zip the whole dist\HappyMeasure folder, not only HappyMeasure.exe."
