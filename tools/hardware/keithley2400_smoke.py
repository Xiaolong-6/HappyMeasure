from __future__ import annotations

import argparse
import csv
import ctypes
import json
import math
import statistics
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

# Expected location in repo: tools/hardware/keithley2400_smoke.py
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from keith_ivt.core.current_range import CurrentRangeControl
from keith_ivt.instrument.serial_2400 import Keithley2400Serial
from keith_ivt.models import SenseMode, SweepConfig, SweepKind, SweepMode, Terminal
from keith_ivt.services.measurement_service import MeasurementService
from keith_ivt.services.power_guard import prevent_system_sleep

CURRENT_RANGE_A = 1e-6
SOURCE_RANGE_V = 0.2
COMPLIANCE_A = 100e-6
FAST_MEASURE_RANGE_A = 1e-3
FAST_DURATION_S = 2.0
OVERFLOW_SENTINEL = 9.91e37
OVERFLOW_TOLERANCE = 0.01e37


class TracedKeithley(Keithley2400Serial):
    """Real 2400 driver with timing/SCPI tracing only; no behavior changes."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.read_starts: list[float] = []
        self.read_ends: list[float] = []
        self.commands: list[tuple[float, str]] = []

    def _write_once(self, command: str) -> None:
        self.commands.append((time.monotonic(), command))
        super()._write_once(command)

    def read_source_and_measure(self) -> tuple[float, float]:
        self.read_starts.append(time.monotonic())
        try:
            return super().read_source_and_measure()
        finally:
            self.read_ends.append(time.monotonic())


class _PowerStatus(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_ubyte),
        ("BatteryFlag", ctypes.c_ubyte),
        ("BatteryLifePercent", ctypes.c_ubyte),
        ("SystemStatusFlag", ctypes.c_ubyte),
        ("BatteryLifeTime", ctypes.c_ulong),
        ("BatteryFullLifeTime", ctypes.c_ulong),
    ]


def get_power_status() -> dict[str, Any]:
    if sys.platform != "win32":
        return {"supported": False, "platform": sys.platform}
    try:
        st = _PowerStatus()
        ok = ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(st))
        if not ok:
            raise OSError("GetSystemPowerStatus failed")
        return {
            "supported": True,
            "ac_line": {0: "battery", 1: "AC", 255: "unknown"}.get(st.ACLineStatus, "unknown"),
            "battery_present": not bool(st.BatteryFlag & 128),
            "battery_percent": None if st.BatteryLifePercent == 255 else int(st.BatteryLifePercent),
        }
    except Exception as exc:
        return {"supported": False, "error": str(exc)}


def ask_yes_no(question: str) -> bool:
    while True:
        ans = input(f"{question} [y/n]: ").strip().lower()
        if ans in {"y", "yes"}:
            return True
        if ans in {"n", "no"}:
            return False


def parse_on_off(raw: str) -> bool | None:
    v = raw.strip().upper()
    if v in {"1", "ON", "TRUE"}:
        return True
    if v in {"0", "OFF", "FALSE"}:
        return False
    return None


def pct(values: list[float], q: float) -> float | None:
    if not values:
        return None
    x = sorted(values)
    pos = (len(x) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return x[lo]
    f = pos - lo
    return x[lo] * (1 - f) + x[hi] * f


def make_cfg(
    port: str,
    baud: int,
    terminal: Terminal,
    nplc: float,
    interval: float,
    points: int,
    *,
    autorange: bool = False,
    continuous: bool = False,
    constant_v: float = 0.0,
) -> SweepConfig:
    # Open-circuit smoke defaults to 0 V, 2-wire only; constant_v is only
    # non-zero for the explicit opt-in Level-1 resistor comparison.
    return SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0.0,
        stop=0.0,
        step=1.0,
        compliance=COMPLIANCE_A,
        nplc=nplc,
        delay_s=0.0,
        port=port,
        baud_rate=baud,
        terminal=terminal,
        sense_mode=SenseMode.TWO_WIRE,
        output_off_after_run=True,
        sweep_kind=SweepKind.CONSTANT_TIME,
        constant_value=constant_v,
        duration_s=max(0.001, (max(points, 1) - 1) * interval),
        continuous_time=continuous,
        interval_s=interval,
        autorange=autorange,
        auto_source_range=False,
        auto_measure_range=autorange,
        source_range=SOURCE_RANGE_V,
        measure_range=CURRENT_RANGE_A,
    )


def make_fast_cfg(
    port: str,
    baud: int,
    terminal: Terminal,
    *,
    duration_s: float = FAST_DURATION_S,
    auto_measure_range: bool = False,
    constant_v: float = 0.0,
) -> SweepConfig:
    """Build a Fast Constant-Time config for release validation (0 V default)."""
    return SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0.0,
        stop=0.0,
        step=1.0,
        compliance=COMPLIANCE_A,
        nplc=0.1,
        delay_s=0.0,
        port=port,
        baud_rate=baud,
        terminal=terminal,
        sense_mode=SenseMode.TWO_WIRE,
        output_off_after_run=True,
        sweep_kind=SweepKind.CONSTANT_TIME,
        constant_value=constant_v,
        duration_s=duration_s,
        continuous_time=False,
        interval_s=0.5,
        autorange=auto_measure_range,
        auto_source_range=False,
        auto_measure_range=auto_measure_range,
        source_range=SOURCE_RANGE_V,
        measure_range=FAST_MEASURE_RANGE_A,
        fast_acquisition=True,
    )


def is_overflow_reading(value: float) -> bool:
    """Mirror the driver overflow sentinel so stored data can be audited."""

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return False
    return abs(abs(numeric) - OVERFLOW_SENTINEL) <= OVERFLOW_TOLERANCE


def acquisition_summary(
    label: str,
    *,
    elapsed: list[float],
    measured: list[float],
    warnings: list[str],
) -> dict[str, Any]:
    """Compute release-contract timing/data-quality statistics for one run."""

    deltas = [b - a for a, b in zip(elapsed, elapsed[1:])]
    overflow_count = sum(1 for value in measured if is_overflow_reading(value))
    nonfinite_count = sum(
        1 for value in measured if not math.isfinite(float(value))
    )
    p95 = pct(deltas, 0.95)
    return {
        "label": label,
        "point_count": len(elapsed),
        "mean_dt_ms": (statistics.mean(deltas) * 1000.0) if deltas else None,
        "median_dt_ms": (statistics.median(deltas) * 1000.0) if deltas else None,
        "p95_dt_ms": (p95 * 1000.0) if p95 is not None else None,
        "min_dt_ms": (min(deltas) * 1000.0) if deltas else None,
        "max_dt_ms": (max(deltas) * 1000.0) if deltas else None,
        "effective_hz": (1.0 / statistics.median(deltas)) if deltas else None,
        "strictly_increasing": bool(deltas) and all(d > 0 for d in deltas),
        "duplicate_elapsed_count": sum(1 for d in deltas if d == 0),
        "overflow_count": overflow_count,
        "invalid_nonfinite_count": nonfinite_count,
        "warnings": list(warnings),
    }


def check_fast_scpi_order(commands: list[tuple[float, str]]) -> tuple[bool, str]:
    """Verify the Fast V-source contract from a traced command sequence."""

    names = [command for _t, command in commands]
    if ":FORM:ELEM CURR" not in names:
        return False, "measurement-only :FORM:ELEM CURR not found"
    try:
        conc = names.index(":SENS:FUNC:CONC OFF")
        form = names.index(":FORM:ELEM CURR")
    except ValueError as exc:
        return False, f"missing Fast setup command: {exc}"
    if conc > form:
        return False, ":SENS:FUNC:CONC OFF must precede :FORM:ELEM CURR"
    telemetry = [
        command
        for command in names
        if command in {":SENS:CURR:RANG:AUTO?", ":SENS:CURR:RANG?"}
    ]
    if telemetry:
        return False, f"range telemetry queries in Fast hot path: {telemetry}"
    return True, "CONC OFF before FORM CURR; no per-sample range queries"


def git_commit() -> str:
    """Return the current commit for artifact provenance, if available."""

    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except Exception:
        return "unknown"
    commit = (completed.stdout or "").strip()
    return commit if completed.returncode == 0 and commit else "unknown"


def run_in_measurement_worker(fn: Callable[[], Any], log: Callable[[str], None]) -> Any:
    box: dict[str, Any] = {}
    errors: list[BaseException] = []

    def target() -> None:
        try:
            log(f"measurement worker thread={threading.get_ident()}")
            with prevent_system_sleep(logger=log):
                box["result"] = fn()
        except BaseException as exc:
            errors.append(exc)

    t = threading.Thread(target=target, name="happymeasure-hardware-smoke")
    t.start()
    t.join()
    if errors:
        raise errors[0]
    return box.get("result")


def run_case(
    port: str,
    baud: int,
    cfg: SweepConfig,
    log: Callable[[str], None],
    *,
    on_point=None,
    should_stop=None,
    should_pause=None,
    control: CurrentRangeControl | None = None,
) -> dict[str, Any]:
    def body() -> dict[str, Any]:
        with TracedKeithley(port=port, baud_rate=baud) as inst:
            idn = inst.identify()
            result = MeasurementService.run_source_meter(
                inst,
                cfg,
                on_point=on_point,
                should_stop=should_stop,
                should_pause=should_pause,
                current_range_control=control,
            )
            try:
                output_off = parse_on_off(inst.query(":OUTP?")) is False
            except Exception:
                output_off = None
            return {
                "idn": idn,
                "points": result.points,
                "warnings": list(result.warnings),
                "starts": inst.read_starts,
                "ends": inst.read_ends,
                "commands": inst.commands,
                "output_off": output_off,
            }

    return run_in_measurement_worker(body, log)


def stats(label: str, nplc: float, interval: float, data: dict[str, Any]) -> dict[str, Any]:
    starts = data["starts"]
    ends = data["ends"]
    deltas = [b - a for a, b in zip(starts, starts[1:])]
    read_durations = [b - a for a, b in zip(starts, ends)]
    idle = [
        starts[i + 1] - ends[i]
        for i in range(min(len(ends), len(starts) - 1))
        if starts[i + 1] >= ends[i]
    ]
    med_dt = statistics.median(deltas) if deltas else None
    med_read = statistics.median(read_durations) if read_durations else None
    med_idle = statistics.median(idle) if idle else None

    classification = "insufficient-data"
    if med_dt is not None and med_read is not None:
        tol = max(0.015, interval * 0.12)
        if med_read >= interval * 0.95:
            classification = (
                "PASS hardware-limited"
                if (med_idle or 0.0) <= max(0.03, interval * 0.35)
                else "WARN idle-gap"
            )
        elif abs(med_dt - interval) <= tol:
            classification = "PASS scheduler-controlled"
        else:
            classification = "WARN cadence-unexpected"

    return {
        "label": label,
        "nplc": nplc,
        "requested_interval_s": interval,
        "points": len(starts),
        "median_delta_s": med_dt,
        "mean_delta_s": statistics.mean(deltas) if deltas else None,
        "std_delta_s": statistics.pstdev(deltas) if len(deltas) > 1 else 0.0,
        "min_delta_s": min(deltas) if deltas else None,
        "max_delta_s": max(deltas) if deltas else None,
        "p95_delta_s": pct(deltas, 0.95),
        "p99_delta_s": pct(deltas, 0.99),
        "median_read_s": med_read,
        "median_idle_s": med_idle,
        "effective_hz": 1.0 / med_dt if med_dt else None,
        "classification": classification,
        "output_off": data["output_off"],
    }


def write_points(path: Path, data: dict[str, Any]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "index", "source", "measured", "elapsed_s", "timestamp",
            "read_start", "read_end", "read_duration",
        ])
        for i, p in enumerate(data["points"]):
            start = data["starts"][i] if i < len(data["starts"]) else ""
            end = data["ends"][i] if i < len(data["ends"]) else ""
            dur = end - start if isinstance(start, float) and isinstance(end, float) else ""
            w.writerow([i + 1, p.source_value, p.measured_value, p.elapsed_s, p.timestamp, start, end, dur])


def add(checks: list[dict[str, str]], name: str, status: str, detail: str) -> None:
    checks.append({"name": name, "status": status, "detail": detail})
    print(f"[{status}] {name}: {detail}")


def main() -> int:
    ap = argparse.ArgumentParser(description="HappyMeasure no-DUT Keithley 2400/2401 smoke/timing runner")
    ap.add_argument("--port", required=True, help="e.g. COM3")
    ap.add_argument("--baud", type=int, default=57600)
    ap.add_argument("--terminal", choices=["front", "rear"], default="rear")
    ap.add_argument("--full", action="store_true", help="add NPLC=1 and range-query characterization")
    ap.add_argument("--power-test", action="store_true", help="add long battery idle/sleep-prevention test")
    ap.add_argument("--power-minutes", type=float, default=8.0)
    ap.add_argument("--output-dir", type=Path)
    ap.add_argument(
        "--release",
        action="store_true",
        help="add the v1.2b1 Fast release block: Standard, Fast fixed-range, "
        "Fast Auto-range, pause/resume, stop/restart, SCPI order and artifact bundle",
    )
    ap.add_argument(
        "--resistor-ohms",
        default=None,
        help="optional Level-1 check against a known resistor, e.g. 10000; use 'ask' to prompt",
    )
    ap.add_argument(
        "--resistor-tolerance",
        type=float,
        default=0.2,
        help="relative tolerance for the resistor comparison",
    )
    args = ap.parse_args()

    terminal = Terminal.FRONT if args.terminal == "front" else Terminal.REAR
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = args.output_dir or ROOT / "hardware_smoke_results" / stamp
    raw_dir = out / "raw_points"
    raw_dir.mkdir(parents=True, exist_ok=True)
    runtime_log = out / "runtime.log"

    checks: list[dict[str, str]] = []
    report: dict[str, Any] = {
        "started": datetime.now().isoformat(),
        "port": args.port,
        "baud": args.baud,
        "terminal": terminal.value,
        "source_V": 0.0,
    }

    def log(msg: str) -> None:
        line = f"{datetime.now().isoformat(timespec='milliseconds')} {msg}"
        print(line)
        with runtime_log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    print("\nHappyMeasure Keithley 2400/2401 NO-DUT hardware smoke")
    print("SAFETY: leave ALL analog terminals/test leads open. Script sources 0 V only.")
    if input("Type OPEN to confirm all analog terminals are unconnected: ").strip().upper() != "OPEN":
        print("Cancelled before any output test.")
        return 2

    try:
        # A. IDN + audible link check. Preserve original beeper state.
        with Keithley2400Serial(args.port, args.baud) as inst:
            inst.output_off()
            idn = inst.identify()
            report["idn"] = idn
            idn_ok = "KEITHLEY" in idn.upper() and any(
                model in idn.upper()
                for model in ("2400", "2401", "2410", "2420", "2430", "2440")
            )
            add(checks, "IDN", "PASS" if idn_ok else "FAIL", idn)
            if not idn_ok:
                raise RuntimeError("Unexpected instrument; measurement tests refused")

            try:
                beeper_initial = parse_on_off(inst.query(":SYST:BEEP:STAT?"))
                report["initial_beeper"] = beeper_initial
            except Exception as exc:
                beeper_initial = None
                report["initial_beeper_error"] = str(exc)

            changed = beeper_initial is False
            try:
                if changed:
                    inst.write(":SYST:BEEP:STAT ON")
                inst.beep()
                time.sleep(0.15)
            finally:
                if changed:
                    inst.write(":SYST:BEEP:STAT OFF")

        heard = ask_yes_no("Did the Keithley emit exactly one short beep?")
        add(checks, "Physical beep", "PASS" if heard else "FAIL", "operator confirmation")
        if beeper_initial is False:
            add(
                checks,
                "App beep edge case",
                "WARN",
                "Beeper was initially OFF. If app Connect does not temporarily enable/restore it, audible confirmation can be silent.",
            )

        # B. Verify real source-delay state after configuration.
        cfg0 = make_cfg(args.port, args.baud, terminal, 0.1, 0.2, 3)
        with Keithley2400Serial(args.port, args.baud) as inst:
            inst.reset()
            inst.configure_for_sweep(cfg0)
            auto_raw = inst.query(":SOUR:DEL:AUTO?")
            delay_raw = inst.query(":SOUR:DEL?")
            inst.output_off()
        delay_ok = parse_on_off(auto_raw) is False and abs(float(delay_raw)) <= 1e-9
        add(checks, "Source delay ownership", "PASS" if delay_ok else "FAIL", f"AUTO={auto_raw}, DEL={delay_raw}")

        # C. Basic 0 V finite read + output-off confirmation.
        zero = run_case(
            args.port, args.baud,
            make_cfg(args.port, args.baud, terminal, 0.1, 0.2, 5),
            log,
            control=CurrentRangeControl(),
        )
        write_points(raw_dir / "zero_volt.csv", zero)
        finite = len(zero["points"]) == 5 and all(
            math.isfinite(p.source_value) and math.isfinite(p.measured_value) for p in zero["points"]
        )
        add(
            checks,
            "0 V open-circuit read",
            "PASS" if finite and zero["output_off"] else "FAIL",
            f"points={len(zero['points'])}, output_off={zero['output_off']}",
        )

        # D. Constant-Time timing matrix.
        cases = [
            (0.1, 0.01, 100),
            (0.1, 0.10, 100),
            (0.1, 0.20, 100),
            (0.1, 0.50, 50),
        ]
        if args.full:
            cases += [
                (0.1, 0.02, 100),
                (0.1, 0.05, 100),
                (0.1, 0.15, 100),
                (1.0, 0.05, 60),
                (1.0, 0.10, 60),
                (1.0, 0.20, 60),
                (1.0, 0.50, 40),
            ]

        timing_rows: list[dict[str, Any]] = []
        for nplc, interval, points in cases:
            label = f"nplc{nplc:g}_dt{interval:g}"
            print(f"\n[TIMING] {label}: {points} points")
            data = run_case(
                args.port, args.baud,
                make_cfg(args.port, args.baud, terminal, nplc, interval, points),
                log,
                control=CurrentRangeControl(),
            )
            write_points(raw_dir / f"{label}.csv", data)
            s = stats(label, nplc, interval, data)
            timing_rows.append(s)
            status = "PASS" if s["classification"].startswith("PASS") and data["output_off"] else "WARN"
            add(
                checks, f"Timing {label}", status,
                f"{s['classification']}; median_dt={s['median_delta_s']}; median_read={s['median_read_s']}; idle={s['median_idle_s']}",
            )
        report["timing"] = timing_rows

        # E. Pause 3 s after point 10; verify rebase/no catch-up burst.
        pause_event = threading.Event()
        pause_once = threading.Event()

        def pause_cb(_p: Any, index: int, _total: int) -> None:
            if index == 10 and not pause_once.is_set():
                pause_once.set()
                pause_event.set()
                threading.Timer(3.0, pause_event.clear).start()

        paused = run_case(
            args.port, args.baud,
            make_cfg(args.port, args.baud, terminal, 0.1, 0.2, 22),
            log,
            on_point=pause_cb,
            should_pause=pause_event.is_set,
            control=CurrentRangeControl(),
        )
        write_points(raw_dir / "pause_resume.csv", paused)
        pause_dts = [b - a for a, b in zip(paused["starts"], paused["starts"][1:])]
        max_gap = max(pause_dts) if pause_dts else 0.0
        post = pause_dts[10:14] if len(pause_dts) >= 14 else []
        pause_ok = max_gap >= 2.5 and bool(post) and statistics.median(post) >= 0.15 and paused["output_off"]
        add(checks, "Pause/resume rebase", "PASS" if pause_ok else "FAIL", f"max_gap={max_gap:.3f}s, post={post}")

        # F. Stop continuous run after 20 points, then immediately restart.
        stop_event = threading.Event()

        def stop_cb(_p: Any, index: int, _total: int) -> None:
            if index >= 20:
                stop_event.set()

        stopped = run_case(
            args.port, args.baud,
            make_cfg(args.port, args.baud, terminal, 0.1, 0.1, 100, continuous=True),
            log,
            on_point=stop_cb,
            should_stop=stop_event.is_set,
            control=CurrentRangeControl(),
        )
        restarted = run_case(
            args.port, args.baud,
            make_cfg(args.port, args.baud, terminal, 0.1, 0.2, 10),
            log,
            control=CurrentRangeControl(),
        )
        stop_ok = (
            20 <= len(stopped["points"]) <= 21
            and stopped["output_off"]
            and len(restarted["points"]) == 10
            and restarted["output_off"]
        )
        add(
            checks, "Stop + immediate restart", "PASS" if stop_ok else "FAIL",
            f"stopped={len(stopped['points'])}, restarted={len(restarted['points'])}",
        )

        # R. v1.2b1 Fast release block: Standard, Fast fixed-range, Fast
        # Auto-range, SCPI order, overflow audit, and the artifact bundle.
        if args.release:
            (out / "idn.txt").write_text(str(report.get("idn", "")), encoding="utf-8")
            release_meta = {
                "git_commit": git_commit(),
                "instrument_idn": report.get("idn"),
                "com_port": args.port,
                "baud": args.baud,
                "terminal": terminal.value,
                "source_mode": "VOLTAGE_SOURCE",
                "source_V": 0.0,
                "compliance_A": COMPLIANCE_A,
                "nplc": 0.1,
                "sense": "TWO_WIRE",
            }
            report["release_metadata"] = release_meta

            std_release = run_case(
                args.port, args.baud,
                make_cfg(args.port, args.baud, terminal, 0.1, 0.2, 10),
                log,
                control=CurrentRangeControl(),
            )
            write_points(out / "standard.csv", std_release)
            std_summary = acquisition_summary(
                "standard",
                elapsed=[p.elapsed_s for p in std_release["points"]],
                measured=[p.measured_value for p in std_release["points"]],
                warnings=std_release["warnings"],
            )
            std_ok = (
                len(std_release["points"]) == 10
                and std_summary["overflow_count"] == 0
                and std_summary["invalid_nonfinite_count"] == 0
                and std_release["output_off"]
            )
            add(
                checks, "Release Standard", "PASS" if std_ok else "FAIL",
                json.dumps(std_summary, default=str),
            )

            fast_runs: dict[str, Any] = {}
            for auto in (False, True):
                name = "fast_auto" if auto else "fast_fixed"
                cfg = make_fast_cfg(args.port, args.baud, terminal, auto_measure_range=auto)
                data = run_case(
                    args.port, args.baud, cfg, log, control=CurrentRangeControl()
                )
                write_points(out / f"{name}.csv", data)
                summary = acquisition_summary(
                    name,
                    elapsed=[p.elapsed_s for p in data["points"]],
                    measured=[p.measured_value for p in data["points"]],
                    warnings=data["warnings"],
                )
                scpi_ok, scpi_detail = check_fast_scpi_order(data["commands"])
                data_ok = (
                    summary["point_count"] > 0
                    and summary["overflow_count"] == 0
                    and summary["invalid_nonfinite_count"] == 0
                    and summary["duplicate_elapsed_count"] == 0
                    and data["output_off"]
                )
                add(
                    checks, f"Release {name}", "PASS" if (data_ok and scpi_ok) else "FAIL",
                    f"{json.dumps(summary, default=str)}; scpi={scpi_detail}",
                )
                fast_runs[name] = {
                    "summary": summary,
                    "scpi_ok": scpi_ok,
                    "scpi_detail": scpi_detail,
                }
                if name == "fast_fixed":
                    with (out / "scpi_trace.txt").open("w", encoding="utf-8") as f:
                        for stamp, command in data["commands"]:
                            f.write(f"{stamp:.6f} {command}\n")
            report["release_fast"] = fast_runs

        # L1. Optional Level-1 resistor comparison (never runs by default).
        resistor_arg = args.resistor_ohms
        if resistor_arg is not None:
            if str(resistor_arg).strip().lower() == "ask":
                resistor_arg = input("Resistor value in ohms for the Level-1 check: ").strip()
            try:
                resistor_ohms = float(resistor_arg)
            except (TypeError, ValueError):
                raise RuntimeError(f"Invalid --resistor-ohms value: {resistor_arg!r}")
            if not math.isfinite(resistor_ohms) or resistor_ohms <= 0:
                raise RuntimeError(f"Invalid --resistor-ohms value: {resistor_arg!r}")
            expected_a = 0.1 / resistor_ohms
            if expected_a >= COMPLIANCE_A * 0.9:
                raise RuntimeError(
                    f"Refusing Level-1 run: expected {expected_a:.3g} A too close "
                    f"to {COMPLIANCE_A:.3g} A compliance."
                )
            tolerance = float(args.resistor_tolerance)
            std_r = run_case(
                args.port, args.baud,
                make_cfg(args.port, args.baud, terminal, 0.1, 0.2, 10, constant_v=0.1),
                log,
                control=CurrentRangeControl(),
            )
            fast_r = run_case(
                args.port, args.baud,
                make_fast_cfg(
                    args.port, args.baud, terminal, duration_s=1.0, constant_v=0.1
                ),
                log,
                control=CurrentRangeControl(),
            )
            write_points(raw_dir / "resistor_standard.csv", std_r)
            write_points(raw_dir / "resistor_fast.csv", fast_r)

            def _median(values: list[float]) -> float:
                finite = [v for v in values if math.isfinite(v)]
                return statistics.median(finite) if finite else float("nan")

            std_med = _median([p.measured_value for p in std_r["points"]])
            fast_med = _median([p.measured_value for p in fast_r["points"]])

            def _rel_err(value: float) -> float:
                if not expected_a or not math.isfinite(value):
                    return float("inf")
                return abs(value - expected_a) / expected_a

            resistor_results = {
                "resistor_ohms": resistor_ohms,
                "expected_A": expected_a,
                "standard_median_A": std_med,
                "fast_median_A": fast_med,
                "standard_relative_error": _rel_err(std_med),
                "fast_relative_error": _rel_err(fast_med),
                "tolerance": tolerance,
            }
            resistor_ok = (
                resistor_results["standard_relative_error"] <= tolerance
                and resistor_results["fast_relative_error"] <= tolerance
                and std_r["output_off"]
                and len(std_r["points"]) == 10
                and len(fast_r["points"]) > 0
            )
            report["resistor"] = resistor_results
            add(
                checks, "Level-1 resistor", "PASS" if resistor_ok else "FAIL",
                json.dumps(resistor_results, default=str),
            )

        # G. Full mode: confirm fixed-range fast path removes repeated range queries.
        if args.full:
            rr: dict[str, Any] = {}
            for auto in (False, True):
                name = "auto" if auto else "fixed"
                data = run_case(
                    args.port, args.baud,
                    make_cfg(args.port, args.baud, terminal, 0.1, 0.01, 30, autorange=auto),
                    log,
                    control=CurrentRangeControl(),
                )
                queries = sum(
                    cmd in {":SENS:CURR:RANG:AUTO?", ":SENS:CURR:RANG?"}
                    for _t, cmd in data["commands"]
                )
                rr[name] = {"queries": queries, "timing": stats(name, 0.1, 0.01, data)}
            report["range"] = rr
            range_ok = rr["fixed"]["queries"] == 0 and rr["auto"]["queries"] > 0
            add(
                checks, "Fixed-range fast path", "PASS" if range_ok else "WARN",
                f"fixed_queries={rr['fixed']['queries']}, auto_queries={rr['auto']['queries']}",
            )

        # H. Optional real Windows battery idle test.
        if args.power_test:
            print("\n[POWER TEST]")
            print("Current Windows power status:", get_power_status())
            input("Unplug AC now, then press Enter. Do not touch mouse/keyboard until the run finishes. ")
            p0 = get_power_status()
            report["power_start"] = p0
            if p0.get("supported") and p0.get("battery_present") and p0.get("ac_line") != "battery":
                if not ask_yes_no("Windows still reports AC. Continue anyway?"):
                    add(checks, "Battery idle test", "SKIP", str(p0))

            skipped = any(c["name"] == "Battery idle test" and c["status"] == "SKIP" for c in checks)
            if not skipped:
                power_stop = threading.Event()
                timer = threading.Timer(max(6.0, args.power_minutes * 60.0), power_stop.set)
                timer.start()
                try:
                    pdata = run_case(
                        args.port, args.baud,
                        make_cfg(args.port, args.baud, terminal, 0.1, 0.5, 10, continuous=True),
                        log,
                        should_stop=power_stop.is_set,
                        control=CurrentRangeControl(),
                    )
                finally:
                    timer.cancel()
                write_points(raw_dir / "power_guard_long.csv", pdata)
                gaps = [b - a for a, b in zip(pdata["starts"], pdata["starts"][1:])]
                max_power_gap = max(gaps) if gaps else float("inf")
                display_off = ask_yes_no("Did the display turn off at least once during the idle test?")
                power_ok = max_power_gap < 5.0 and pdata["output_off"]
                add(checks, "Battery idle test", "PASS" if power_ok else "FAIL", f"points={len(pdata['points'])}, max_gap={max_power_gap:.3f}s")
                add(checks, "Display may turn off", "PASS" if display_off else "WARN", "operator observation")
                report["power"] = {
                    "start": p0,
                    "end": get_power_status(),
                    "points": len(pdata["points"]),
                    "max_gap_s": max_power_gap,
                    "display_off": display_off,
                }

    except KeyboardInterrupt:
        add(checks, "Runner", "FAIL", "KeyboardInterrupt")
    except BaseException as exc:
        add(checks, "Runner", "FAIL", f"{type(exc).__name__}: {exc}")
        report["fatal_error"] = f"{type(exc).__name__}: {exc}"

    report["finished"] = datetime.now().isoformat()
    report["checks"] = checks
    report["overall"] = (
        "FAIL" if any(c["status"] == "FAIL" for c in checks)
        else "WARN" if any(c["status"] == "WARN" for c in checks)
        else "PASS"
    )

    (out / "summary.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    with (out / "summary.txt").open("w", encoding="utf-8") as f:
        for c in checks:
            f.write(f"[{c['status']}] {c['name']}: {c['detail']}\n")
        f.write(f"\nOVERALL: {report['overall']}\n")

    if report.get("timing"):
        with (out / "timing_stats.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(report["timing"][0].keys()))
            w.writeheader()
            w.writerows(report["timing"])

    print("\n" + (out / "summary.txt").read_text(encoding="utf-8"))
    print("Artifacts:", out)
    return 1 if report["overall"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
