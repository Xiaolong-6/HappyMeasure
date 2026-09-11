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


def main() -> None:
    print(f"Full validation for HappyMeasure {version.VERSION} ({version.RELEASE_STAGE})")
    ok = compileall.compile_dir(str(SRC), quiet=1)
    ok = compileall.compile_dir(str(ROOT / "tests"), quiet=1) and ok
    if not ok:
        raise SystemExit("compileall failed")
    print("PASS compileall src tests")

    for domain in ("common", "happymeasure", "map_reconstruction"):
        run([sys.executable, "-m", "pytest", f"tests/{domain}", "-q"])

    run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--cov=keith_ivt",
            "--cov=map_reconstruction",
            "--cov-report=term",
            "-q",
        ]
    )
    print("PASS domain tests and coverage gate")


if __name__ == "__main__":
    main()
