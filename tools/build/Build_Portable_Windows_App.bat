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
call :log Building HappyMeasure portable Windows app
call :log Working directory: "%CD%"
call :log Supported build Python versions, in order: 3.12, 3.11, 3.13
call :log ==========================================

if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "packaging\build" rmdir /s /q "packaging\build"
if exist "packaging\dist" rmdir /s /q "packaging\dist"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys; allowed={(3,12),(3,11),(3,13)}; raise SystemExit(0 if sys.version_info[:2] in allowed else 1)" >nul 2>&1
    if errorlevel 1 (
        call :log Existing .venv is missing, broken, or not a supported build Python; deleting .venv
        rmdir /s /q ".venv"
    )
)

if not exist ".venv\Scripts\python.exe" (
    set "PICK_LABEL=pick_python"
    call :%PICK_LABEL%
    if errorlevel 1 goto :fail
    call :log Creating build virtual environment with !PY_CMD!
    !PY_CMD! -m venv .venv
    if errorlevel 1 goto :fail
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :fail

python -c "import sys; allowed={(3,12),(3,11),(3,13)}; print('Build Python:', sys.version.replace(chr(10), ' ')); print('Executable:', sys.executable); raise SystemExit(0 if sys.version_info[:2] in allowed else 1)"
if errorlevel 1 (
    call :log ERROR: Active build environment is not a supported build Python.
    goto :fail
)

python -m pip install --upgrade pip
if errorlevel 1 goto :fail
set "PYTHONPATH=%PROJECT_ROOT%\src"
python -m pip install matplotlib pyserial pydantic pytest pytest-cov ruff black mypy
if errorlevel 1 goto :fail
python -m pip install --upgrade pyinstaller
if errorlevel 1 goto :fail

call :log Running import smoke check...
python -c "import keith_ivt; from keith_ivt.ui.simple_app import main; import matplotlib; import serial; print('Smoke check OK')"
if errorlevel 1 goto :fail

call :log Running test suite...
python -m pytest
if errorlevel 1 goto :fail

call :log Running PyInstaller...
if not exist "build" mkdir "build"
if not exist "dist" mkdir "dist"
pyinstaller --noconfirm --clean --distpath dist --workpath build packaging\HappyMeasure.spec
set "PI_STATUS=%ERRORLEVEL%"
if not "%PI_STATUS%"=="0" goto :fail

if not exist "dist\HappyMeasure\HappyMeasure.exe" (
    call :log ERROR: dist\HappyMeasure\HappyMeasure.exe was not created.
    goto :fail
)

if not exist "dist\HappyMeasure\logs" mkdir "dist\HappyMeasure\logs"
if not exist "dist\HappyMeasure\examples" mkdir "dist\HappyMeasure\examples"
if not exist "dist\HappyMeasure\config" mkdir "dist\HappyMeasure\config"
copy /Y "packaging\README_FIRST_PORTABLE.txt" "dist\HappyMeasure\README_FIRST.txt" >nul 2>&1
copy /Y "docs\HARDWARE_VALIDATION_PROTOCOL.md" "dist\HappyMeasure\HARDWARE_VALIDATION_PROTOCOL.md" >nul 2>&1
copy /Y "docs\HARDWARE_DRY_RUN_GUIDE.md" "dist\HappyMeasure\HARDWARE_DRY_RUN_GUIDE.md" >nul 2>&1
xcopy /E /I /Y "config\*.json" "dist\HappyMeasure\config\" >nul 2>&1
xcopy /E /I /Y "examples\*" "dist\HappyMeasure\examples\" >nul 2>&1

for /f "usebackq delims=" %%V in (`python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"`) do set "APP_VERSION=%%V"
set "ZIP_PATH=dist\HappyMeasure-%APP_VERSION%-windows-portable.zip"
if exist "%ZIP_PATH%" del /q "%ZIP_PATH%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'dist\HappyMeasure' -DestinationPath '%ZIP_PATH%' -CompressionLevel Optimal"
if errorlevel 1 goto :fail
if exist "build" rmdir /s /q "build"

call :log ==========================================
call :log Build finished.
call :log Portable app folder:
call :log "%CD%\dist\HappyMeasure"
call :log Main executable:
call :log "%CD%\dist\HappyMeasure\HappyMeasure.exe"
call :log Portable zip:
call :log "%CD%\%ZIP_PATH%"
call :log ==========================================
call :log Deliver the zip or the whole dist\HappyMeasure folder, not only HappyMeasure.exe.

echo.
echo Press any key to continue . . .
pause >nul
exit /b 0

:pick_python
set "PY_CMD="
for %%V in (3.12 3.11 3.13) do (
    py -%%V -c "import sys; raise SystemExit(0 if sys.version_info[:2] == tuple(map(int, '%%V'.split('.'))) else 1)" >nul 2>&1
    if not errorlevel 1 (
        set "PY_CMD=py -%%V"
        exit /b 0
    )
)
for %%V in (3.12 3.11 3.13) do (
    python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == tuple(map(int, '%%V'.split('.'))) else 1)" >nul 2>&1
    if not errorlevel 1 (
        set "PY_CMD=python"
        exit /b 0
    )
)
call :log ERROR: No supported Python was found.
call :log Install Python 3.12, 3.11, or 3.13, or make sure the Python launcher can run one of them.
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
