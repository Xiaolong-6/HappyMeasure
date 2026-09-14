from __future__ import annotations

import subprocess
import sys


def test_hardware_preflight_imports_in_fresh_interpreter() -> None:
    code = (
        "import keith_ivt.hardware_preflight; "
        "from keith_ivt.instrument.serial_2400 import Keithley2400Serial; "
        "print(Keithley2400Serial.__name__)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Keithley2400Serial" in result.stdout
