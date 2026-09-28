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


def test_happymeasure_spec_avoids_matplotlib_development_tree():
    spec = (ROOT / "packaging" / "HappyMeasure.spec").read_text(encoding="utf-8")
    assert "collect_all" not in spec
    assert '"matplotlib.backends.backend_tkagg"' in spec
    assert '"matplotlib.tests"' in spec
    assert '"matplotlib.testing"' in spec
    assert '"matplotlib.sphinxext"' in spec


def test_portable_build_docs_exist():
    assert (ROOT / "docs/WINDOWS_PORTABLE_BUILD.md").exists()
    assert (ROOT / "packaging/README_FIRST_PORTABLE.txt").exists()


def test_application_icon_assets_and_portable_icon_are_declared():
    assert (ROOT / "src/keith_ivt/assets/happymeasure.png").is_file()
    assert (ROOT / "src/keith_ivt/assets/happymeasure.ico").is_file()
    spec = (ROOT / "packaging/HappyMeasure.spec").read_text(encoding="utf-8")
    assert "icon=str(HAPPYMEASURE_ICON)" in spec


def test_release_artifact_audit_and_package_ci_are_wired():
    audit = ROOT / "tools" / "release" / "audit_portable_artifacts.py"
    assert audit.is_file()
    text = audit.read_text(encoding="utf-8")
    assert "release-artifacts.json" in text
    assert "sha256_file" in text
    assert "MapReconstruction" not in text
    assert "MAP_ZIP_LIMIT" not in text

    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "package-smoke:" in workflow
    assert "Windows portable package smoke (Python 3.12)" in workflow
    assert "audit_portable_artifacts.py" in workflow
    assert "HappyMeasure.exe" in workflow
    assert "MapReconstruction.exe" not in workflow
    assert "actions/upload-artifact@v6" in workflow


def test_retired_desktop_map_packaging_files_are_absent():
    retired = (
        ROOT / "Run_Map_Reconstruction.bat",
        ROOT / "packaging" / "map_reconstruction_entry.py",
        ROOT / "packaging" / "MapReconstruction.spec",
        ROOT / "packaging" / "README_FIRST_MAP_PORTABLE.txt",
        ROOT / "tools" / "build" / "Build_Portable_Map_Reconstruction.bat",
        ROOT / "tools" / "build" / "Build_Portable_Map_Reconstruction.ps1",
    )
    for path in retired:
        assert not path.exists(), path
