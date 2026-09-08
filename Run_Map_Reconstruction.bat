@echo off
setlocal EnableExtensions

rem Space-safe launcher for the optional Map Reconstruction GUI.
rem Optional CSV path arguments are forwarded to: python -m map_reconstruction

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%" || (
    echo Failed to enter project directory: "%PROJECT_DIR%"
    pause
    exit /b 1
)

set "VENV_PY=%PROJECT_DIR%.venv\Scripts\python.exe"
set "VENV_PYW=%PROJECT_DIR%.venv\Scripts\pythonw.exe"
set "PYTHONPATH=%PROJECT_DIR%src;%PYTHONPATH%"

if not exist "%VENV_PY%" (
    echo [ERROR] Project virtual environment not found:
    echo         "%VENV_PY%"
    echo Create .venv first, then install the map extras with:
    echo   .venv\Scripts\python.exe -m pip install -e ".[map]"
    pause
    exit /b 1
)

if not exist "%VENV_PYW%" (
    echo [ERROR] GUI Python executable not found:
    echo         "%VENV_PYW%"
    pause
    exit /b 1
)

"%VENV_PY%" -c "import PySide6, pyqtgraph" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Map GUI dependencies are missing from .venv.
    echo Install them with:
    echo   .venv\Scripts\python.exe -m pip install -e ".[map]"
    pause
    exit /b 1
)

echo Starting Map Reconstruction...
start "" /D "%PROJECT_DIR%" "%VENV_PYW%" -m map_reconstruction %*
exit /b 0
