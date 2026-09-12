$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location -LiteralPath $ProjectRoot

$LogDir = Join-Path $ProjectRoot "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$BuildLog = Join-Path $LogDir "build_portable_map_reconstruction.log"
$BuildLogWritable = $true
# Prefer the Qt-gate Python first; keep the pyproject >=3.11 floor otherwise.
$PythonVersions = @("3.12", "3.11", "3.13")
$BuildVenv = ".venv-build-map"

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

function Test-PythonVersion(
    [string]$Version,
    [string]$Command,
    [string[]]$CommandArgs = @()
) {
    try {
        & $Command @CommandArgs -c "import sys; expected=tuple(map(int, '$Version'.split('.'))); raise SystemExit(0 if sys.version_info[:2] == expected else 1)" *> $null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Invoke-PythonCommand([string[]]$PythonCmd, [string[]]$InvocationArgs) {
    $Command = $PythonCmd[0]
    $CommandArgs = @()
    if ($PythonCmd.Count -gt 1) {
        $CommandArgs = $PythonCmd[1..($PythonCmd.Count - 1)]
    }
    & $Command @CommandArgs @InvocationArgs
}

function Pick-Python {
    foreach ($Version in $PythonVersions) {
        if (Test-PythonVersion $Version "py" @("-$Version")) {
            return @("py", "-$Version")
        }
    }
    foreach ($Version in $PythonVersions) {
        if (Test-PythonVersion $Version "python") {
            return @("python")
        }
    }
    throw "No supported Python was found. Install Python 3.12, 3.11, or 3.13 (pyproject requires-python >=3.11)."
}

Write-Step "=========================================="
Write-Step "Building Map Reconstruction portable Windows app"
Write-Step "Working directory: $ProjectRoot"
Write-Step "Supported build Python versions, in order: $($PythonVersions -join ', ')"
Write-Step "=========================================="

Write-Step "Automated validation is a packaging precondition, not part of this script."
Write-Step "Run the owned gates first: tests/common + tests/happymeasure, then the Map Qt gate."

Remove-Item -Recurse -Force -LiteralPath "build" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force -LiteralPath "dist\MapReconstruction" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force -LiteralPath "packaging\build" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force -LiteralPath "packaging\dist" -ErrorAction SilentlyContinue

$VenvPython = Join-Path $ProjectRoot "$BuildVenv\Scripts\python.exe"
if (Test-Path -LiteralPath $VenvPython) {
    & $VenvPython -c "import sys; allowed={(3,12),(3,11),(3,13)}; raise SystemExit(0 if sys.version_info[:2] in allowed else 1)" *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Step "Existing $BuildVenv is not a supported build Python; deleting $BuildVenv (developer .venv is never touched)"
        Remove-Item -Recurse -Force -LiteralPath $BuildVenv
    }
}

if (-not (Test-Path -LiteralPath $VenvPython)) {
    $PythonCmd = Pick-Python
    Write-Step "Creating build virtual environment with $($PythonCmd -join ' ')"
    Invoke-PythonCommand $PythonCmd @("-m", "venv", $BuildVenv)
}

& ".\$BuildVenv\Scripts\Activate.ps1"
python -c "import sys; allowed={(3,12),(3,11),(3,13)}; print('Build Python:', sys.version.replace(chr(10), ' ')); print('Executable:', sys.executable); raise SystemExit(0 if sys.version_info[:2] in allowed else 1)"
Assert-LastCommand "Python version check"

New-Item -ItemType Directory -Force -Path ".tmp-build" | Out-Null
New-Item -ItemType Directory -Force -Path ".pip-cache" | Out-Null
$env:TEMP = Join-Path $ProjectRoot ".tmp-build"
$env:TMP = $env:TEMP
$env:PIP_CACHE_DIR = Join-Path $ProjectRoot ".pip-cache"
$env:PYTHONPATH = Join-Path $ProjectRoot "src"
# pyproject.toml owns dependencies; the Map build installs the .[map] extra.
python -m pip install --upgrade pip
Assert-LastCommand "pip upgrade"
python -m pip install -e ".[map]"
Assert-LastCommand "Map dependency install"
python -m pip install --upgrade pyinstaller
Assert-LastCommand "PyInstaller install"

Write-Step "Running import smoke check..."
$env:QT_QPA_PLATFORM = "offscreen"
python -c "import map_reconstruction; import PySide6, pyqtgraph, numpy; print('Smoke check OK', map_reconstruction.__version__)"
Assert-LastCommand "Import smoke check"

Write-Step "Running PyInstaller..."
New-Item -ItemType Directory -Force -Path "build" | Out-Null
New-Item -ItemType Directory -Force -Path "dist" | Out-Null
pyinstaller --noconfirm --clean --distpath dist --workpath build packaging\MapReconstruction.spec
Assert-LastCommand "PyInstaller build"

if (-not (Test-Path -LiteralPath "dist\MapReconstruction\MapReconstruction.exe")) {
    throw "dist\MapReconstruction\MapReconstruction.exe was not created."
}

New-Item -ItemType Directory -Force -Path "dist\MapReconstruction\logs" | Out-Null
Copy-Item -Force "packaging\README_FIRST_MAP_PORTABLE.txt" "dist\MapReconstruction\README_FIRST.txt" -ErrorAction SilentlyContinue
Copy-Item -Force "docs\MAP_PROJECT_FORMAT.md" "dist\MapReconstruction\MAP_PROJECT_FORMAT.md" -ErrorAction SilentlyContinue

$Version = python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"
$ZipPath = Join-Path $ProjectRoot "dist\MapReconstruction-$Version-windows-portable.zip"
Remove-Item -Force -LiteralPath $ZipPath -ErrorAction SilentlyContinue
Compress-Archive -Path "dist\MapReconstruction" -DestinationPath $ZipPath -CompressionLevel Optimal
Remove-Item -Recurse -Force -LiteralPath "build" -ErrorAction SilentlyContinue

Write-Step "=========================================="
Write-Step "Build finished."
Write-Step "Portable app folder: $ProjectRoot\dist\MapReconstruction"
Write-Step "Main executable: $ProjectRoot\dist\MapReconstruction\MapReconstruction.exe"
Write-Step "Portable zip: $ZipPath"
Write-Step "=========================================="
Write-Step "Deliver the zip or the whole dist\MapReconstruction folder, not only MapReconstruction.exe."
