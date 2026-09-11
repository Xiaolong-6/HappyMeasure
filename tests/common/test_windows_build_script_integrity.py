from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD_DIR = ROOT / "tools" / "build"


def test_batch_build_script_has_single_python_selection_flow():
    text = (BUILD_DIR / "Build_Portable_Windows_App.bat").read_text(encoding="utf-8")
    assert text.count(":pick_python") == 1
    assert text.count(":find_python") == 0
    assert "Creating build virtual environment with !PY_CMD!" in text
    assert "for %%V in (3.12 3.11 3.13)" in text


def test_batch_build_script_has_no_accidental_duplicate_header():
    text = (BUILD_DIR / "Build_Portable_Windows_App.bat").read_text(encoding="utf-8")
    assert text.count("Building HappyMeasure portable Windows app") == 1
    assert text.count('if not exist ".venv\\Scripts\\python.exe"') == 1


def test_all_build_scripts_remind_release_owner_to_verify_asset_digest():
    for path in (
        BUILD_DIR / "Build_Portable_Windows_App.bat",
        BUILD_DIR / "Build_Portable_Windows_App.ps1",
        BUILD_DIR / "Build_Portable_Windows_App_Python314.bat",
        BUILD_DIR / "Build_Portable_Windows_App_Python314.ps1",
    ):
        text = path.read_text(encoding="utf-8")
        assert "RELEASE REMINDER" in text
        assert "sha256: digest" in text
        assert "types-pyserial" in text


def test_powershell_python_probe_does_not_shadow_automatic_args_variable():
    for name in (
        "Build_Portable_Windows_App.ps1",
        "Build_Portable_Windows_App_Python314.ps1",
    ):
        text = (BUILD_DIR / name).read_text(encoding="utf-8")
        assert "[string[]]$Args" not in text
        assert "[string[]]$CommandArgs" in text
        assert "[string[]]$InvocationArgs" in text
