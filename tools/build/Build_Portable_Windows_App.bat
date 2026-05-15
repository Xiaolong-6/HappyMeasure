@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."
for %%I in ("%PROJECT_ROOT%") do set "PROJECT_ROOT=%%~fI"
cd /d "%PROJECT_ROOT%"

set "BUILD_LOG_DIR=%PROJECT_ROOT%\logs"
if not exist "%BUILD_LOG_DIR%" mkdir "%BUILD_LOG_DIR%"
set "BUILD_LOG=%BUILD_LOG_DIR%\build_portable_windows_app.log"

call :log ==========================================
call :log Building HappyMeasure portable Windows app with Python 3.14
call :log Working directory: "%CD%"
call :log ==========================================

if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

rem This build script intentionally targets Python 3.14 only.
rem It does not search for 3.13/3.12/3.11.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,14) else 1)" >nul 2>&1
    if errorlevel 1 (
        call :log Existing .venv is missing, broken, or not Python 3.14; deleting .venv
        rmdir /s /q ".venv"
    )
)

if not exist ".venv\Scripts\python.exe" (
    call :pick_python314
    if errorlevel 1 goto :fail
    call :log Creating build virtual environment with !PY_CMD!
    !PY_CMD! -m venv .venv
    if errorlevel 1 goto :fail
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :fail

python -c "import sys; print('Build Python:', sys.version.replace(chr(10), ' ')); print('Executable:', sys.executable); raise SystemExit(0 if sys.version_info[:2] == (3,14) else 1)"
if errorlevel 1 (
    call :log ERROR: Active build environment is not Python 3.14.
    goto :fail
)

python -m pip install --upgrade pip
if errorlevel 1 goto :fail
python -m pip install -e ".[dev]"
if errorlevel 1 goto :fail
python -m pip install --upgrade pyinstaller
if errorlevel 1 goto :fail

call :log Running Python 3.14 smoke check...
python -c "import keith_ivt; from keith_ivt.ui.simple_app import main; import matplotlib; import serial; print('Smoke check OK')"
if errorlevel 1 goto :fail

call :log Skipping full pytest validation for Python 3.14 build.
call :log Reason: Windows/Python 3.14 can keep temporary log files locked during pytest cleanup.
call :log Run simulator + hardware preflight manually after packaging.

call :log Running PyInstaller...
pushd packaging
pyinstaller --noconfirm --clean HappyMeasure.spec
set "PI_STATUS=%ERRORLEVEL%"
popd
if not "%PI_STATUS%"=="0" goto :fail

if not exist "dist\HappyMeasure\HappyMeasure.exe" (
    call :log ERROR: dist\HappyMeasure\HappyMeasure.exe was not created.
    goto :fail
)

if not exist "dist\HappyMeasure\logs" mkdir "dist\HappyMeasure\logs"
if not exist "dist\HappyMeasure\examples" mkdir "dist\HappyMeasure\examples"
copy /Y "packaging\README_FIRST_PORTABLE.txt" "dist\HappyMeasure\README_FIRST.txt" >nul 2>&1
copy /Y "docs\HARDWARE_VALIDATION_PROTOCOL.md" "dist\HappyMeasure\HARDWARE_VALIDATION_PROTOCOL.md" >nul 2>&1
copy /Y "docs\HARDWARE_DRY_RUN_GUIDE.md" "dist\HappyMeasure\HARDWARE_DRY_RUN_GUIDE.md" >nul 2>&1

call :log ==========================================
call :log Build finished.
call :log Portable app folder:
call :log "%CD%\dist\HappyMeasure"
call :log Main executable:
call :log "%CD%\dist\HappyMeasure\HappyMeasure.exe"
call :log ==========================================
call :log Next step: zip the whole dist\HappyMeasure folder, not only HappyMeasure.exe.

echo.
echo Press any key to continue . . .
pause >nul
exit /b 0

:pick_python314
set "PY_CMD="
py -3.14 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,14) else 1)" >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=py -3.14"
    exit /b 0
)
python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,14) else 1)" >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=python"
    exit /b 0
)
call :log ERROR: Python 3.14 was not found.
call :log Install Python 3.14 or make sure the Python launcher can run: py -3.14
call :log Current PATH python, if any:
python --version 2>> "%BUILD_LOG%"
exit /b 1

:log
echo %*
echo %*>> "%BUILD_LOG%"
exit /b 0

:fail
call :log ERROR: Build failed. See "%BUILD_LOG%" for details.
echo.
echo Press any key to continue . . .
pause >nul
exit /b 1
