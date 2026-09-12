from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_pyinstaller_entry_exists_and_imports_main():
    text = (ROOT / "packaging" / "happymeasure_entry.py").read_text(encoding="utf-8")
    assert "from happymeasure.__main__ import run" in text
    assert "run()" in text


def test_windows_build_scripts_are_space_path_safe():
    bat = (ROOT / "tools/build/Build_Portable_Windows_App.bat").read_text(encoding="utf-8")
    ps1 = (ROOT / "tools/build/Build_Portable_Windows_App.ps1").read_text(encoding="utf-8")
    assert 'cd /d "%PROJECT_ROOT%"' in bat
    assert '".venv-build\\Scripts\\python.exe"' in bat
    assert "Set-Location -LiteralPath $ProjectRoot" in ps1
    assert "Join-Path" in ps1


def test_map_portable_build_files_exist():
    assert (ROOT / "packaging" / "map_reconstruction_entry.py").is_file()
    assert (ROOT / "packaging" / "MapReconstruction.spec").is_file()
    assert (ROOT / "packaging" / "README_FIRST_MAP_PORTABLE.txt").is_file()
    assert (ROOT / "tools" / "build" / "Build_Portable_Map_Reconstruction.bat").is_file()
    assert (ROOT / "tools" / "build" / "Build_Portable_Map_Reconstruction.ps1").is_file()
    spec = (ROOT / "packaging" / "MapReconstruction.spec").read_text(encoding="utf-8")
    assert 'name="MapReconstruction"' in spec
    assert "icon=str(MAP_ICON)" in spec
    bat = (ROOT / "tools" / "build" / "Build_Portable_Map_Reconstruction.bat").read_text(
        encoding="utf-8"
    )
    assert 'cd /d "%PROJECT_ROOT%"' in bat
    assert 'cd /d "%PROJECT_DIR%"' not in bat


def test_map_spec_uses_narrow_runtime_collection():
    spec = (ROOT / "packaging" / "MapReconstruction.spec").read_text(encoding="utf-8")
    assert "collect_all" not in spec
    assert 'hookspath=[str(PROJECT_ROOT / "packaging" / "hooks")]' in spec
    assert '"PySide6.QtWebEngineCore"' in spec
    assert (ROOT / "packaging" / "hooks" / "hook-PySide6.QtCore.py").is_file()
    assert (ROOT / "packaging" / "hooks" / "hook-PySide6.QtGui.py").is_file()


def test_portable_build_docs_exist():
    assert (ROOT / "docs/WINDOWS_PORTABLE_BUILD.md").exists()
    assert (ROOT / "packaging/README_FIRST_PORTABLE.txt").exists()


def test_application_icon_assets_and_portable_icon_are_declared():
    assert (ROOT / "src/keith_ivt/assets/happymeasure.png").is_file()
    assert (ROOT / "src/keith_ivt/assets/happymeasure.ico").is_file()
    assert (ROOT / "src/map_reconstruction/assets/map_reconstruction.png").is_file()
    assert (ROOT / "src/map_reconstruction/assets/map_reconstruction.ico").is_file()
    spec = (ROOT / "packaging/HappyMeasure.spec").read_text(encoding="utf-8")
    assert "icon=str(HAPPYMEASURE_ICON)" in spec
