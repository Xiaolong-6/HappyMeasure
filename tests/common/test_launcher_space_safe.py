from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="ignore")


def test_main_batch_launcher_quotes_project_paths():
    text = read("Run_HappyMeasure.bat")
    required = [
        'set "PROJECT_DIR=%~dp0"',
        'cd /d "%PROJECT_DIR%"',
        'set "PYTHONPATH=%PROJECT_DIR%\\src;%PYTHONPATH%"',
        'python -m venv "%PROJECT_DIR%\\.venv"',
        '"%VENV_PY%" -m pip install -e "%PROJECT_DIR%"',
        '"%VENV_PY%" -m happymeasure',
        '"%VENV_PY%" -m keith_ivt',
    ]
    for needle in required:
        assert needle in text


def test_main_powershell_launcher_uses_literal_paths():
    text = read("Run_HappyMeasure.ps1")
    for needle in (
        "$ProjectDir = Split-Path -Parent $PSCommandPath",
        "Set-Location -LiteralPath $ProjectDir",
        "Test-Path -LiteralPath $VenvPy",
        "& $VenvPy -m pip install -e $ProjectDir",
        "& $VenvPy -m happymeasure",
    ):
        assert needle in text


def test_tool_launchers_set_pythonpath_and_quote_paths():
    for rel in (
        "tools/hardware/Real_Hardware_Preflight.bat",
        "tools/validation/Run_Full_Validation.bat",
        "tools/validation/Run_Core_Validation.bat",
        "tools/diagnostics/Run_Diagnostics.bat",
    ):
        text = read(rel)
        assert 'set "PROJECT_DIR=' in text
        assert 'set "PYTHONPATH=%PROJECT_DIR%\\src;%PYTHONPATH%"' in text
        assert '"%PY%"' in text

    for rel in (
        "tools/validation/Run_Full_Validation.ps1",
        "tools/validation/Run_Core_Validation.ps1",
        "tools/diagnostics/Run_Diagnostics.ps1",
    ):
        text = read(rel)
        assert "Resolve-Path -LiteralPath" in text
        assert "Set-Location -LiteralPath $Root" in text
        assert "& $Py" in text


def test_launchers_detect_stale_virtualenv_python():
    main_bat = read("Run_HappyMeasure.bat")
    assert "Existing virtual environment is stale" in main_bat
    assert '"%VENV_PY%" -c "import sys; print(sys.executable)"' in main_bat

    main_ps1 = read("Run_HappyMeasure.ps1")
    assert "Existing .venv is stale" in main_ps1
    assert '& $VenvPy -c "import sys; print(sys.executable)"' in main_ps1
