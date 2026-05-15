@echo off
setlocal EnableExtensions

rem HappyMeasure launcher with smart recovery.
rem Space-safe: every project path is quoted and resolved from this script location.

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%" || (
    echo Failed to enter project directory: "%PROJECT_DIR%"
    echo If this is a network path, map the share to a drive letter or copy the project locally.
    pause
    exit /b 1
)

set "EXITCODE=0"
set "PROJECT_DIR=%CD%"
set "VENV_PY=%PROJECT_DIR%\.venv\Scripts\python.exe"
set "PYTHONPATH=%PROJECT_DIR%\src;%PYTHONPATH%"

echo ============================================
echo HappyMeasure Launcher
echo Working directory: "%PROJECT_DIR%"
echo ============================================
echo.

if not exist "%VENV_PY%" (
    echo [INFO] Virtual environment not found. Creating...
    call :CREATE_OR_REPAIR_VENV
    if errorlevel 1 goto END
)

if not exist "%PROJECT_DIR%\.venv\pyvenv.cfg" (
    echo [INFO] Virtual environment incomplete. Recreating...
    rmdir /s /q "%PROJECT_DIR%\.venv" 2>nul
    call :CREATE_OR_REPAIR_VENV
    if errorlevel 1 goto END
)

rem A copied/synced venv can keep an absolute reference to another Windows user
rem profile, e.g. C:\Users\carll\... . The python.exe file may exist but cannot
rem start. Validate it before launch and rebuild if stale.
"%VENV_PY%" -c "import sys; print(sys.executable)" >nul 2>nul
if errorlevel 1 (
    echo [INFO] Existing virtual environment is stale or points to a missing base Python. Recreating...
    rmdir /s /q "%PROJECT_DIR%\.venv" 2>nul
    call :CREATE_OR_REPAIR_VENV
    if errorlevel 1 goto END
)

echo [1/3] Attempting to launch HappyMeasure...
echo.
"%VENV_PY%" -m keith_ivt
set "EXITCODE=%ERRORLEVEL%"

if "%EXITCODE%"=="0" (
    echo.
    echo [SUCCESS] HappyMeasure exited normally.
    goto END
)

echo.
echo [2/3] Launch failed with code %EXITCODE%. Diagnosing...
echo.

if "%EXITCODE%"=="1" (
    echo [DIAGNOSIS] Possible missing dependencies or corrupted installation.
    echo [ACTION] Repairing virtual environment...
    echo.

    if exist "%PROJECT_DIR%\.venv" (
        echo Backing up old virtual environment...
        if exist "%PROJECT_DIR%\.venv.backup" rmdir /s /q "%PROJECT_DIR%\.venv.backup" 2>nul
        move "%PROJECT_DIR%\.venv" "%PROJECT_DIR%\.venv.backup" >nul 2>&1
    )

    call :CREATE_OR_REPAIR_VENV
    if errorlevel 1 goto END

    echo.
    echo Retrying launch after repair...
    echo.
    "%VENV_PY%" -m keith_ivt
    set "EXITCODE=%ERRORLEVEL%"

    if "%EXITCODE%"=="0" (
        echo.
        echo [SUCCESS] HappyMeasure launched successfully after repair!
        goto END
    )

    echo.
    echo [ERROR] Repair attempt failed. Trying fallback method...
    echo.

    echo [FALLBACK] Launching with direct PYTHONPATH no venv...
    python -m keith_ivt
    set "EXITCODE=%ERRORLEVEL%"

    if "%EXITCODE%"=="0" (
        echo.
        echo [SUCCESS] Fallback launch successful!
        echo [NOTE] Consider recreating venv for better isolation.
        goto END
    )
)

echo.
echo ============================================
echo [ERROR] All launch attempts failed code: %EXITCODE%
echo ============================================
echo.
echo Troubleshooting steps:
echo 1. Run tools\validation\Run_Full_Validation.bat for full diagnostics
echo 2. Check logs\error.log for detailed error messages
echo 3. Ensure Python 3.10+ is installed and in PATH
echo 4. Verify pyproject.toml exists and is valid
echo.
goto END

:CREATE_OR_REPAIR_VENV
echo Creating fresh virtual environment...
python -m venv "%PROJECT_DIR%\.venv"
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    echo Check that Python is installed and available in PATH.
    set "EXITCODE=1"
    exit /b 1
)

if not exist "%VENV_PY%" (
    echo [ERROR] Virtual environment creation failed - python.exe not found.
    set "EXITCODE=1"
    exit /b 1
)

echo.
echo [3/3] Installing dependencies...
"%VENV_PY%" -m pip install --upgrade pip >nul 2>&1
"%VENV_PY%" -m pip install -e "%PROJECT_DIR%"
if errorlevel 1 (
    echo.
    echo [WARNING] Editable install failed. Trying fallback launch with PYTHONPATH later...
    exit /b 1
)
exit /b 0

:END
pause
exit /b %EXITCODE%