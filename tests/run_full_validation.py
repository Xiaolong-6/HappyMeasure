from __future__ import annotations

import compileall
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TEST = ROOT / "tests" / "test_legacy_ui_layout_contracts.py"

sys.path.insert(0, str(SRC))
from keith_ivt import version  # noqa: E402


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    completed = subprocess.run(cmd, cwd=ROOT)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main() -> None:
    print(f"Full validation for HappyMeasure {version.VERSION} ({version.RELEASE_STAGE})")
    print("Quality gates: compileall, legacy UI contracts, full pytest, and coverage >=95% for the unit-testable core/hardware subset. Tk widgets and real hardware entrypoints are omitted from coverage and handled by smoke/bench protocols.")
    ok = compileall.compile_dir(str(SRC), quiet=1)
    ok = compileall.compile_dir(str(ROOT / "tests"), quiet=1) and ok
    if not ok:
        raise SystemExit("compileall failed")
    print("PASS compileall src tests")
    run([sys.executable, str(TEST.relative_to(ROOT))])
    run([sys.executable, "-m", "pytest", "-q"])
    run([sys.executable, "-m", "pytest", "--cov=keith_ivt", "--cov-report=term", "-q"])
    print("PASS current alpha validation")


if __name__ == "__main__":
    main()
