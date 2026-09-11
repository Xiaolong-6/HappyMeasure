from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from time import perf_counter
from typing import Any, Callable

from keith_ivt.drivers.base import instrument_model_from_idn
from keith_ivt.instrument.serial_2400 import Keithley2400Serial

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"
MANUAL = "MANUAL"

_SUPPORTED_2400_MODELS = ("2400", "2401", "2410", "2420", "2430", "2440")


@dataclass(frozen=True)
class HardwareDiagnosticCheck:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class HardwareDiagnosticReport:
    created_at: str
    port: str
    baud_rate: int
    instrument_idn: str
    checks: tuple[HardwareDiagnosticCheck, ...]

    @property
    def overall(self) -> str:
        if any(check.status == FAIL for check in self.checks):
            return FAIL
        if any(check.status == WARN for check in self.checks):
            return WARN
        return PASS

    def to_text(self) -> str:
        lines = [
            "HappyMeasure safe hardware diagnostics",
            f"Created: {self.created_at}",
            f"Port: {self.port}",
            f"Baud: {self.baud_rate}",
            f"Instrument: {self.instrument_idn or '--'}",
            f"Overall: {self.overall}",
            "",
            "Safety contract: communication/output-off checks only; source output is never enabled.",
            "",
        ]
        lines.extend(f"[{check.status}] {check.name}: {check.detail}" for check in self.checks)
        return "\n".join(lines)


def _output_is_off(raw: str) -> bool:
    value = str(raw).strip().upper()
    if value in {"OFF", "FALSE"}:
        return True
    try:
        return float(value) == 0.0
    except (TypeError, ValueError):
        return False


def _supported_identity(idn: str) -> bool:
    """Validate the Keithley model field without matching serial/firmware text."""

    text = str(idn or "").upper()
    if "KEITHLEY" not in text:
        return False
    return instrument_model_from_idn(idn) in _SUPPORTED_2400_MODELS


def _report(
    port: str,
    baud_rate: int,
    idn: str,
    checks: list[HardwareDiagnosticCheck],
) -> HardwareDiagnosticReport:
    return HardwareDiagnosticReport(
        created_at=datetime.now().isoformat(timespec="seconds"),
        port=port,
        baud_rate=baud_rate,
        instrument_idn=idn,
        checks=tuple(checks),
    )


def run_hardware_self_test(
    port: str,
    baud_rate: int,
    *,
    timeout_s: float = 5.0,
    instrument_factory: Callable[..., Any] = Keithley2400Serial,
) -> HardwareDiagnosticReport:
    """Run a conservative real-instrument communication diagnostic.

    The routine deliberately does not reset/configure the SMU, issue READ?,
    set a source value, or enable output. It sends OUTPUT OFF before and after
    each connection, verifies :OUTP?, identifies the instrument, exercises the
    driver's state-preserving beep helper, and reconnects once.

    The caller owns the operator-facing no-DUT confirmation. This function is
    intentionally usable without Tk so the safety contract can be unit-tested.
    """

    checks: list[HardwareDiagnosticCheck] = []
    idn = ""
    first_connection_ok = False
    proceed = True

    try:
        with instrument_factory(
            port=port, baud_rate=int(baud_rate), timeout=float(timeout_s)
        ) as inst:
            try:
                try:
                    inst.output_off()
                    checks.append(
                        HardwareDiagnosticCheck(
                            "Initial OUTPUT OFF",
                            PASS,
                            "OUTPUT OFF command completed before any other instrument action.",
                        )
                    )
                except Exception as exc:
                    proceed = False
                    checks.append(
                        HardwareDiagnosticCheck(
                            "Initial OUTPUT OFF",
                            FAIL,
                            f"Could not force output off: {type(exc).__name__}: {exc}",
                        )
                    )

                if proceed:
                    started = perf_counter()
                    try:
                        idn = str(inst.identify()).strip()
                    except Exception as exc:
                        proceed = False
                        checks.append(
                            HardwareDiagnosticCheck(
                                "Instrument identity",
                                FAIL,
                                f"*IDN? failed: {type(exc).__name__}: {exc}",
                            )
                        )
                    else:
                        latency_ms = (perf_counter() - started) * 1000.0
                        checks.append(
                            HardwareDiagnosticCheck(
                                "Serial communication",
                                PASS,
                                f"*IDN? returned in {latency_ms:.1f} ms.",
                            )
                        )

                if proceed:
                    if not _supported_identity(idn):
                        proceed = False
                        checks.append(
                            HardwareDiagnosticCheck(
                                "Instrument identity",
                                FAIL,
                                f"Unexpected or unvalidated instrument: {idn or '--'}",
                            )
                        )
                    else:
                        checks.append(
                            HardwareDiagnosticCheck(
                                "Instrument identity",
                                PASS,
                                idn,
                            )
                        )

                if proceed:
                    try:
                        output_state = str(inst.query(":OUTP?")).strip()
                    except Exception as exc:
                        proceed = False
                        checks.append(
                            HardwareDiagnosticCheck(
                                "Output-state verification",
                                FAIL,
                                f":OUTP? failed: {type(exc).__name__}: {exc}",
                            )
                        )
                    else:
                        if not _output_is_off(output_state):
                            proceed = False
                            checks.append(
                                HardwareDiagnosticCheck(
                                    "Output-state verification",
                                    FAIL,
                                    f"Instrument reported output state {output_state!r} after OUTPUT OFF.",
                                )
                            )
                        else:
                            checks.append(
                                HardwareDiagnosticCheck(
                                    "Output-state verification",
                                    PASS,
                                    f"Instrument reported {output_state!r} (OFF).",
                                )
                            )

                if proceed:
                    try:
                        inst.beep()
                        checks.append(
                            HardwareDiagnosticCheck(
                                "Beeper command",
                                PASS,
                                "State-preserving short beep command completed.",
                            )
                        )
                        checks.append(
                            HardwareDiagnosticCheck(
                                "Physical beep",
                                MANUAL,
                                "Confirm that exactly one short beep was audible.",
                            )
                        )
                    except Exception as exc:
                        checks.append(
                            HardwareDiagnosticCheck(
                                "Beeper command",
                                WARN,
                                f"Communication remains usable, but beep failed: {type(exc).__name__}: {exc}",
                            )
                        )
                    first_connection_ok = True
            finally:
                try:
                    inst.output_off()
                    checks.append(
                        HardwareDiagnosticCheck(
                            "First-connection cleanup",
                            PASS,
                            "OUTPUT OFF completed before closing the first serial session.",
                        )
                    )
                except Exception as exc:
                    checks.append(
                        HardwareDiagnosticCheck(
                            "First-connection cleanup",
                            FAIL,
                            f"OUTPUT OFF cleanup failed: {type(exc).__name__}: {exc}",
                        )
                    )
    except Exception as exc:
        checks.append(
            HardwareDiagnosticCheck(
                "Serial connection",
                FAIL,
                f"Could not open/use {port}: {type(exc).__name__}: {exc}",
            )
        )
        return _report(port, int(baud_rate), idn, checks)

    if not first_connection_ok or any(check.status == FAIL for check in checks):
        return _report(port, int(baud_rate), idn, checks)

    try:
        with instrument_factory(
            port=port, baud_rate=int(baud_rate), timeout=float(timeout_s)
        ) as inst:
            try:
                inst.output_off()
                second_idn = str(inst.identify()).strip()
                output_state = str(inst.query(":OUTP?")).strip()
                reconnect_ok = second_idn == idn and _output_is_off(output_state)
                checks.append(
                    HardwareDiagnosticCheck(
                        "Disconnect / reconnect",
                        PASS if reconnect_ok else FAIL,
                        (
                            "Reconnected to the same instrument with output OFF."
                            if reconnect_ok
                            else (
                                f"Reconnect mismatch: IDN={second_idn!r}, "
                                f"OUTP={output_state!r}."
                            )
                        ),
                    )
                )
            finally:
                try:
                    inst.output_off()
                    checks.append(
                        HardwareDiagnosticCheck(
                            "Final OUTPUT OFF",
                            PASS,
                            "OUTPUT OFF completed before the diagnostic released the port.",
                        )
                    )
                except Exception as exc:
                    checks.append(
                        HardwareDiagnosticCheck(
                            "Final OUTPUT OFF",
                            FAIL,
                            f"Final OUTPUT OFF failed: {type(exc).__name__}: {exc}",
                        )
                    )
    except Exception as exc:
        checks.append(
            HardwareDiagnosticCheck(
                "Disconnect / reconnect",
                FAIL,
                f"Reconnect failed: {type(exc).__name__}: {exc}",
            )
        )

    return _report(port, int(baud_rate), idn, checks)


__all__ = [
    "PASS",
    "WARN",
    "FAIL",
    "MANUAL",
    "HardwareDiagnosticCheck",
    "HardwareDiagnosticReport",
    "run_hardware_self_test",
]
