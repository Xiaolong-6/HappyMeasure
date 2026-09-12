from __future__ import annotations

import compileall
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

sys.path.insert(0, str(SRC))
from keith_ivt import version  # noqa: E402


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    completed = subprocess.run(cmd, cwd=ROOT)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def require_map_dependencies() -> None:
    try:
        import PySide6  # noqa: F401
        import pyqtgraph  # noqa: F401
    except ModuleNotFoundError:
        print("Full validation requires Map dependencies, but PySide6/pyqtgraph are missing.")
        print("Install them first, then rerun:")
        print('    python -m pip install -e ".[dev,map]"')
        raise SystemExit(2)


def main() -> None:
    print(f"Full validation for HappyMeasure {version.VERSION} ({version.RELEASE_STAGE})")
    ok = compileall.compile_dir(str(SRC), quiet=1)
    ok = compileall.compile_dir(str(ROOT / "tests"), quiet=1) and ok
    if not ok:
        raise SystemExit("compileall failed")
    print("PASS compileall src tests")

    for domain in ("common", "happymeasure"):
        run([sys.executable, "-m", "pytest", f"tests/{domain}", "-q"])

    require_map_dependencies()
    run([sys.executable, "-m", "pytest", "tests/map_reconstruction", "-q"])

    # Map Reconstruction is an independent Qt gate.  Keep the 95% coverage
    # threshold scoped to the HappyMeasure core, whose release contract owns
    # that threshold; combining the optional Map UI/core would lower the
    # aggregate percentage without changing either gate's result.
    run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/common",
            "tests/happymeasure",
            "--cov=keith_ivt",
            "--cov-report=term",
            "-q",
        ]
    )
    print("PASS core/Map domain tests and core coverage gate")


if __name__ == "__main__":
    main()
