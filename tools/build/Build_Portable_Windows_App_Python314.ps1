$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location -LiteralPath $ProjectRoot

$LogDir = Join-Path $ProjectRoot "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$BuildLog = Join-Path $LogDir "build_portable_windows_app.log"
$BuildLogWritable = $true

function Write-Step([string]$Message) {
    Write-Host $Message
    if (-not $script:BuildLogWritable) {
        return
    }
    try {
        Add-Content -LiteralPath $BuildLog -Value $Message
    } catch {
        Write-Warning "Could not write build log: $($_.Exception.Message)"
        $script:BuildLogWritable = $false
    }
}

function Assert-LastCommand([string]$Step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE."
    }
}

function Test-Python314([string]$Command, [string[]]$CommandArgs = @()) {
    try {
        & $Command @CommandArgs -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,14) else 1)" *> $null
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

function Invoke-PythonCommand([string[]]$PythonCmd, [string[]]$InvocationArgs) {
    $Command = $PythonCmd[0]
    $CommandArgs = @()
    if ($PythonCmd.Count -gt 1) {
        $CommandArgs = $PythonCmd[1..($PythonCmd.Count - 1)]
    }
    & $Command @CommandArgs @InvocationArgs
}

Write-Step "=========================================="
Write-Step "Building HappyMeasure portable Windows app with Python 3.14"
Write-Step "Working directory: $ProjectRoot"
Write-Step "=========================================="

Remove-Item -Recurse -Force -LiteralPath "build" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force -LiteralPath "dist" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force -LiteralPath "packaging\build" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force -LiteralPath "packaging\dist" -ErrorAction SilentlyContinue

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
    Invoke-PythonCommand $PythonCmd @("-m", "venv", ".venv")
}

& ".\.venv\Scripts\Activate.ps1"
python -c "import sys; print('Build Python:', sys.version.replace(chr(10), ' ')); print('Executable:', sys.executable); raise SystemExit(0 if sys.version_info[:2] == (3,14) else 1)"
Assert-LastCommand "Python version check"

New-Item -ItemType Directory -Force -Path ".tmp-build" | Out-Null
New-Item -ItemType Directory -Force -Path ".pip-cache" | Out-Null
$env:TEMP = Join-Path $ProjectRoot ".tmp-build"
$env:TMP = $env:TEMP
$env:PIP_CACHE_DIR = Join-Path $ProjectRoot ".pip-cache"
$env:PYTHONPATH = Join-Path $ProjectRoot "src"
python -m pip install --upgrade pip
Assert-LastCommand "pip upgrade"
python -m pip install matplotlib pyserial pydantic pytest pytest-cov ruff black mypy types-pyserial
Assert-LastCommand "project dependency install"
python -m pip install --upgrade pyinstaller
Assert-LastCommand "PyInstaller install"

Write-Step "Running Python 3.14 smoke check..."
python -c "import keith_ivt; from keith_ivt.ui.simple_app import main; import matplotlib; import serial; print('Smoke check OK')"
Assert-LastCommand "Import smoke check"

Write-Step "Skipping full pytest validation for Python 3.14 build. Run simulator + hardware preflight manually after packaging."

Write-Step "Running PyInstaller..."
New-Item -ItemType Directory -Force -Path "build" | Out-Null
New-Item -ItemType Directory -Force -Path "dist" | Out-Null
pyinstaller --noconfirm --clean --distpath dist --workpath build packaging\HappyMeasure.spec
Assert-LastCommand "PyInstaller build"

if (-not (Test-Path -LiteralPath "dist\HappyMeasure\HappyMeasure.exe")) {
    throw "dist\HappyMeasure\HappyMeasure.exe was not created."
}

New-Item -ItemType Directory -Force -Path "dist\HappyMeasure\logs" | Out-Null
New-Item -ItemType Directory -Force -Path "dist\HappyMeasure\examples" | Out-Null
New-Item -ItemType Directory -Force -Path "dist\HappyMeasure\config" | Out-Null
Copy-Item -Force "packaging\README_FIRST_PORTABLE.txt" "dist\HappyMeasure\README_FIRST.txt" -ErrorAction SilentlyContinue
Copy-Item -Force "docs\HARDWARE_VALIDATION_PROTOCOL.md" "dist\HappyMeasure\HARDWARE_VALIDATION_PROTOCOL.md" -ErrorAction SilentlyContinue
Copy-Item -Force "docs\HARDWARE_DRY_RUN_GUIDE.md" "dist\HappyMeasure\HARDWARE_DRY_RUN_GUIDE.md" -ErrorAction SilentlyContinue
Copy-Item -Force "config\*.json" "dist\HappyMeasure\config\" -ErrorAction SilentlyContinue
Copy-Item -Recurse -Force "examples\*" "dist\HappyMeasure\examples\" -ErrorAction SilentlyContinue

$Version = python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"
$ZipPath = Join-Path $ProjectRoot "dist\HappyMeasure-$Version-windows-portable.zip"
Remove-Item -Force -LiteralPath $ZipPath -ErrorAction SilentlyContinue
Compress-Archive -Path "dist\HappyMeasure" -DestinationPath $ZipPath -CompressionLevel Optimal
Remove-Item -Recurse -Force -LiteralPath "build" -ErrorAction SilentlyContinue

Write-Step "=========================================="
Write-Step "Build finished."
Write-Step "Portable app folder: $ProjectRoot\dist\HappyMeasure"
Write-Step "Main executable: $ProjectRoot\dist\HappyMeasure\HappyMeasure.exe"
Write-Step "Portable zip: $ZipPath"
Write-Step "=========================================="
Write-Step "Deliver the zip or the whole dist\HappyMeasure folder, not only HappyMeasure.exe."
Write-Step "RELEASE REMINDER: After uploading the zip, verify GitHub release metadata exposes a sha256: digest."
Write-Step "Without that digest, HappyMeasure will intentionally offer manual download only."
