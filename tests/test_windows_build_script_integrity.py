from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_batch_build_script_has_single_pick_python_label():
    text = (ROOT / "tools" / "build" / "Build_Portable_Windows_App.bat").read_text(encoding="utf-8")
    assert text.count(":pick_python") == 1
    assert text.count(":find_python") == 0
    assert "Creating build virtual environment with !PY_CMD!" in text
    assert "for %%V in (3.12 3.11 3.13)" in text


def test_batch_build_script_has_no_accidental_inline_duplicate_header():
    text = (ROOT / "tools" / "build" / "Build_Portable_Windows_App.bat").read_text(encoding="utf-8")
    assert text.count("Building HappyMeasure portable Windows app") == 1
    assert text.count("if not exist \".venv\\Scripts\\python.exe\"") == 1
