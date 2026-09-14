$ErrorActionPreference = "Stop"

# Space-safe launcher: all paths are resolved from this script and passed with LiteralPath / call operator.
$ProjectDir = Split-Path -Parent $PSCommandPath
Set-Location -LiteralPath $ProjectDir
$env:PYTHONPATH = (Join-Path $ProjectDir "src") + ";" + $env:PYTHONPATH
$VenvPy = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$VenvDir = Join-Path $ProjectDir ".venv"

function Test-CompatiblePython {
    param(
        [Parameter(Mandatory = $true)][string]$Exe,
        [string[]]$PrefixArgs = @()
    )
    try {
        & $Exe @PrefixArgs -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" *> $null
        return ($LASTEXITCODE -eq 0)
    }
    catch {
        return $false
    }
}

function Find-CompatiblePython {
    $candidates = @(
        @{ Exe = "py"; Args = @("-3.14") },
        @{ Exe = "py"; Args = @("-3.13") },
        @{ Exe = "py"; Args = @("-3.12") },
        @{ Exe = "py"; Args = @("-3.11") },
        @{ Exe = "python"; Args = @() }
    )
    foreach ($candidate in $candidates) {
        if (Test-CompatiblePython -Exe $candidate.Exe -PrefixArgs $candidate.Args) {
            return $candidate
        }
    }
    return $null
}

function New-HappyMeasureVenv {
    param([Parameter(Mandatory = $true)]$Bootstrap)
    $exe = $Bootstrap.Exe
    $prefix = @($Bootstrap.Args)
    Write-Host "Creating local virtual environment..."
    & $exe @prefix -m venv $VenvDir
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $VenvPy)) {
        throw "Failed to create .venv with a compatible Python interpreter."
    }
}

Write-Host "HappyMeasure desktop launcher"
Write-Host "Working directory: $ProjectDir"

$VenvUsable = $false
if (Test-Path -LiteralPath $VenvPy) {
    $VenvUsable = Test-CompatiblePython -Exe $VenvPy
    if ($VenvUsable) {
        $version = (& $VenvPy --version 2>&1 | Out-String).Trim()
        Write-Host "Using existing virtual environment: $version"
    }
    else {
        Write-Host "Existing .venv is stale, broken, or uses Python older than 3.11. Recreating it..."
        Remove-Item -LiteralPath $VenvDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}
elseif (Test-Path -LiteralPath $VenvDir) {
    Write-Host "Existing .venv is incomplete or broken. Recreating it..."
    Remove-Item -LiteralPath $VenvDir -Recurse -Force -ErrorAction SilentlyContinue
}

$Bootstrap = $null
if (-not $VenvUsable) {
    $Bootstrap = Find-CompatiblePython
    if ($null -eq $Bootstrap) {
        throw "No usable Python 3.11 or newer interpreter was found. Run 'py -0p' to list installed Python interpreters."
    }
    $exe = $Bootstrap.Exe
    $prefix = @($Bootstrap.Args)
    $version = (& $exe @prefix --version 2>&1 | Out-String).Trim()
    Write-Host "Bootstrap interpreter: $version ($exe $($prefix -join ' '))"
    New-HappyMeasureVenv -Bootstrap $Bootstrap
}

if (-not (Test-Path -LiteralPath $VenvPy)) {
    throw ".venv\Scripts\python.exe was not created."
}

# A copied/synced venv can keep an absolute reference to a different Windows
# profile. Validate the interpreter itself rather than trusting the copied path.
if (-not (Test-CompatiblePython -Exe $VenvPy)) {
    Write-Host "Existing .venv is stale or points to a missing/unsupported base Python. Recreating it..."
    Remove-Item -LiteralPath $VenvDir -Recurse -Force -ErrorAction SilentlyContinue
    if ($null -eq $Bootstrap) {
        $Bootstrap = Find-CompatiblePython
    }
    if ($null -eq $Bootstrap) {
        throw "No usable Python 3.11 or newer interpreter was found for .venv repair."
    }
    New-HappyMeasureVenv -Bootstrap $Bootstrap
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
