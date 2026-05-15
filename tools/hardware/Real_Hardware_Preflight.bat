@echo off
setlocal EnableExtensions
set "PROJECT_DIR=%~dp0\..\.."
cd /d "%PROJECT_DIR%" || exit /b 1
set "PROJECT_DIR=%CD%"
set "PYTHONPATH=%PROJECT_DIR%\src;%PYTHONPATH%"
set "VENV_PY=%PROJECT_DIR%\.venv\Scripts\python.exe"
if exist "%VENV_PY%" (
    "%VENV_PY%" -c "import sys" >nul 2>nul
    if errorlevel 1 (
        echo [INFO] Ignoring stale/broken .venv; using system Python.
        set "PY=python"
    ) else (
        set "PY=%VENV_PY%"
    )
) else (
    set "PY=python"
)
echo HappyMeasure real-hardware preflight: IDN query + output OFF only.
echo Usage: edit COM port below if needed.
set "PORT=COM3"
set "BAUD=9600"
"%PY%" -m keith_ivt.hardware_preflight "%PORT%" --baud "%BAUD%"
set "EXITCODE=%ERRORLEVEL%"
pause
exit /b %EXITCODE%
