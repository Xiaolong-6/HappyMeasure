@echo off
setlocal EnableExtensions
set "PROJECT_DIR=%~dp0\..\.."
pushd "%PROJECT_DIR%" >nul || exit /b 1
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
"%PY%" "%PROJECT_DIR%\tests\test_legacy_ui_layout_contracts.py"
set "EXITCODE=%ERRORLEVEL%"
popd >nul
pause
exit /b %EXITCODE%
