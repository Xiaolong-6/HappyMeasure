from pathlib import Path


def test_pyinstaller_entry_exists_and_imports_main():
    entry = Path("packaging/happymeasure_entry.py")
    text = entry.read_text(encoding="utf-8")
    assert "from happymeasure.__main__ import run" in text
    assert "run()" in text


def test_windows_build_scripts_are_space_path_safe():
    bat = Path("tools/build/Build_Portable_Windows_App.bat").read_text(encoding="utf-8")
    ps1 = Path("tools/build/Build_Portable_Windows_App.ps1").read_text(encoding="utf-8")
    assert 'cd /d "%PROJECT_ROOT%"' in bat
    assert '".venv\\Scripts\\python.exe"' in bat
    assert "Set-Location -LiteralPath $ProjectRoot" in ps1
    assert "Join-Path" in ps1


def test_portable_build_docs_exist():
    assert Path("docs/WINDOWS_PORTABLE_BUILD.md").exists()
    assert Path("packaging/README_FIRST_PORTABLE.txt").exists()


def test_application_icon_assets_and_portable_icon_are_declared():
    assert Path("src/keith_ivt/assets/happymeasure.png").is_file()
    assert Path("src/keith_ivt/assets/happymeasure.ico").is_file()
    assert Path("src/map_reconstruction/assets/map_reconstruction.png").is_file()
    assert Path("src/map_reconstruction/assets/map_reconstruction.ico").is_file()
    spec = Path("packaging/HappyMeasure.spec").read_text(encoding="utf-8")
    assert "icon=str(HAPPYMEASURE_ICON)" in spec
