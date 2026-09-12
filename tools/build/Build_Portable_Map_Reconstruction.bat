@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."
for %%I in ("%PROJECT_ROOT%") do set "PROJECT_ROOT=%%~fI"
cd /d "%PROJECT_ROOT%"

set "BUILD_LOG_DIR=%PROJECT_ROOT%\logs"
if not exist "%BUILD_LOG_DIR%" mkdir "%BUILD_LOG_DIR%"
set "BUILD_LOG=%BUILD_LOG_DIR%\build_portable_map_reconstruction.log"

call :log ==========================================
call :log Building Map Reconstruction portable Windows app
call :log Working directory: "%CD%"
call :log Supported build Python versions, in order: 3.12, 3.11, 3.13
call :log ==========================================

call :log Automated validation is a packaging precondition, not part of this script.
call :log Run the owned gates first: tests/common + tests/happymeasure, then the Map Qt gate.

if exist "build" rmdir /s /q "build"
if exist "dist\MapReconstruction" rmdir /s /q "dist\MapReconstruction"
if exist "packaging\build" rmdir /s /q "packaging\build"
if exist "packaging\dist" rmdir /s /q "packaging\dist"

if exist ".venv-build-map\Scripts\python.exe" (
    ".venv-build-map\Scripts\python.exe" -c "import sys; allowed={(3,12),(3,11),(3,13)}; raise SystemExit(0 if sys.version_info[:2] in allowed else 1)" >nul 2>&1
    if errorlevel 1 (
        call :log Existing .venv-build-map is not a supported build Python; deleting it (developer .venv is never touched)
        rmdir /s /q ".venv-build-map"
    )
)

if not exist ".venv-build-map\Scripts\python.exe" (
    set "PICK_LABEL=pick_python"
    call :%PICK_LABEL%
    if errorlevel 1 goto :fail
    call :log Creating build virtual environment with !PY_CMD!
    !PY_CMD! -m venv .venv-build-map
    if errorlevel 1 goto :fail
)

call ".venv-build-map\Scripts\activate.bat"
if errorlevel 1 goto :fail

python -c "import sys; allowed={(3,12),(3,11),(3,13)}; print('Build Python:', sys.version.replace(chr(10), ' ')); print('Executable:', sys.executable); raise SystemExit(0 if sys.version_info[:2] in allowed else 1)"
if errorlevel 1 (
    call :log ERROR: Active build environment is not a supported build Python.
    goto :fail
)

if not exist ".tmp-build" mkdir ".tmp-build"
if not exist ".pip-cache" mkdir ".pip-cache"
set "TEMP=%PROJECT_ROOT%\.tmp-build"
set "TMP=%PROJECT_ROOT%\.tmp-build"
set "PIP_CACHE_DIR=%PROJECT_ROOT%\.pip-cache"
set "PYTHONPATH=%PROJECT_ROOT%\src"
python -m pip install --upgrade pip
if errorlevel 1 goto :fail
python -m pip install -e ".[map]"
if errorlevel 1 goto :fail
python -m pip install --upgrade pyinstaller
if errorlevel 1 goto :fail

call :log Running import smoke check...
set "QT_QPA_PLATFORM=offscreen"
python -c "import map_reconstruction; import PySide6, pyqtgraph, numpy; print('Smoke check OK', map_reconstruction.__version__)"
if errorlevel 1 goto :fail

call :log Running PyInstaller...
if not exist "build" mkdir "build"
if not exist "dist" mkdir "dist"
pyinstaller --noconfirm --clean --distpath dist --workpath build packaging\MapReconstruction.spec
set "PI_STATUS=%ERRORLEVEL%"
if not "%PI_STATUS%"=="0" goto :fail

if not exist "dist\MapReconstruction\MapReconstruction.exe" (
    call :log ERROR: dist\MapReconstruction\MapReconstruction.exe was not created.
    goto :fail
)

if not exist "dist\MapReconstruction\logs" mkdir "dist\MapReconstruction\logs"
copy /Y "packaging\README_FIRST_MAP_PORTABLE.txt" "dist\MapReconstruction\README_FIRST.txt" >nul 2>&1
copy /Y "docs\MAP_PROJECT_FORMAT.md" "dist\MapReconstruction\MAP_PROJECT_FORMAT.md" >nul 2>&1

for /f "usebackq delims=" %%V in (`python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"`) do set "APP_VERSION=%%V"
set "ZIP_PATH=dist\MapReconstruction-%APP_VERSION%-windows-portable.zip"
if exist "%ZIP_PATH%" del /q "%ZIP_PATH%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'dist\MapReconstruction' -DestinationPath '%ZIP_PATH%' -CompressionLevel Optimal"
if errorlevel 1 goto :fail
if exist "build" rmdir /s /q "build"

call :log ==========================================
call :log Build finished.
call :log Portable app folder:
call :log "%CD%\dist\MapReconstruction"
call :log Main executable:
call :log "%CD%\dist\MapReconstruction\MapReconstruction.exe"
call :log Portable zip:
call :log "%CD%\%ZIP_PATH%"
call :log ==========================================
call :log Deliver the zip or the whole dist\MapReconstruction folder, not only MapReconstruction.exe.

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
call :log Install Python 3.12, 3.11, or 3.13 (pyproject requires-python ^>=3.11^).
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
