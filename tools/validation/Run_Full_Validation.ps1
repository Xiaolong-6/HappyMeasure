$ErrorActionPreference = "Stop"
$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
Set-Location -LiteralPath $Root
$env:PYTHONPATH = (Join-Path $Root "src") + ";" + $env:PYTHONPATH
$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $Py) {
    & $Py -c "import sys" *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Ignoring stale/broken .venv; using system Python."
        $Py = "python"
    }
} else {
    $Py = "python"
}
& $Py (Join-Path $Root "tests\run_full_validation.py")
