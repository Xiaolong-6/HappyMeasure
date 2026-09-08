@echo off
setlocal EnableExtensions
set "PROJECT_DIR=%~dp0\..\.."
cd /d "%PROJECT_DIR%" || exit /b 1
set "PYTHONPATH=%PROJECT_DIR%\src;%PYTHONPATH%"

set "VENV_PY=%PROJECT_DIR%\.venv\Scripts\python.exe"
if exist "%VENV_PY%" (
    "%VENV_PY%" -c "import sys" >nul 2>nul
    if errorlevel 1 (set "PY=python") else (set "PY=%VENV_PY%")
) else (
    set "PY=python"
)

rem EDIT THESE IF NEEDED
set "PORT=COM3"
set "BAUD=9600"
set "TERMINAL=rear"

echo.
echo HappyMeasure Keithley 2400/2401 no-DUT smoke
echo ========================================
echo Port=%PORT%  Baud=%BAUD%  Terminal=%TERMINAL%
echo.
echo [1] QUICK core smoke/timing
echo [2] FULL timing + range characterization
echo [3] FULL + 8-minute battery sleep-prevention test
set /p "MODE=Choose 1/2/3: "

if "%MODE%"=="1" (
  "%PY%" tools\hardware\keithley2400_smoke.py --port "%PORT%" --baud "%BAUD%" --terminal "%TERMINAL%"
) else if "%MODE%"=="2" (
  "%PY%" tools\hardware\keithley2400_smoke.py --port "%PORT%" --baud "%BAUD%" --terminal "%TERMINAL%" --full
) else if "%MODE%"=="3" (
  "%PY%" tools\hardware\keithley2400_smoke.py --port "%PORT%" --baud "%BAUD%" --terminal "%TERMINAL%" --full --power-test --power-minutes 8
) else (
  echo Invalid choice.
  pause
  exit /b 2
)

set "EXITCODE=%ERRORLEVEL%"
echo.
echo Exit code: %EXITCODE%
pause
exit /b %EXITCODE%
