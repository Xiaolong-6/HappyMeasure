from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import importlib.util
import os
import platform
import sys
from datetime import datetime

from keith_ivt.app_config import AppPaths
from keith_ivt.version import APP_NAME, VERSION


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str

    def line(self) -> str:
        return f"{'PASS' if self.ok else 'WARN'} {self.name}: {self.detail}"


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def collect_diagnostics(root: str | os.PathLike[str] | None = None) -> list[Check]:
    paths = AppPaths.from_root(root)
    checks: list[Check] = [
        Check("app", True, f"{APP_NAME} {VERSION}"),
        Check("python", sys.version_info >= (3, 11), sys.version.replace("\n", " ")),
        Check("platform", True, platform.platform()),
        Check("working_directory", paths.root.exists(), str(paths.root)),
        Check("src_package", (paths.root / "src" / "keith_ivt").exists(), str(paths.root / "src" / "keith_ivt")),
        Check("pyproject", (paths.root / "pyproject.toml").exists(), str(paths.root / "pyproject.toml")),
        Check("matplotlib", _module_available("matplotlib"), "required for plotting"),
        Check("serial", _module_available("serial"), "pyserial; required for real hardware"),
        Check("tkinter", _module_available("tkinter"), "required for UI"),
    ]
    for p in (paths.logs, paths.exports, paths.autosaves, paths.presets, paths.settings):
        try:
            p.mkdir(parents=True, exist_ok=True)
            probe = p / ".write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            checks.append(Check(f"writable_{p.name}", True, str(p)))
        except Exception as exc:
            checks.append(Check(f"writable_{p.name}", False, f"{p}: {exc}"))
    try:
        import serial.tools.list_ports  # type: ignore
        ports = [port.device for port in serial.tools.list_ports.comports()]
        checks.append(Check("serial_ports", True, ", ".join(ports) if ports else "no ports detected"))
    except Exception as exc:
        checks.append(Check("serial_ports", False, str(exc)))
    return checks


def write_diagnostics_report(root: str | os.PathLike[str] | None = None, path: str | os.PathLike[str] | None = None) -> Path:
    paths = AppPaths.from_root(root)
    paths.ensure()
    out = Path(path) if path is not None else paths.logs / "diagnostics_report.txt"
    checks = collect_diagnostics(paths.root)
    lines = [
        f"HappyMeasure diagnostics report",
        f"created_at: {datetime.now().isoformat(timespec='seconds')}",
        "",
        *[check.line() for check in checks],
        "",
        "Overall: " + ("PASS" if all(c.ok for c in checks if c.name not in {"serial", "serial_ports"}) else "WARN"),
    ]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out
