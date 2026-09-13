from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from keith_ivt.instrument.serial_2400 import Keithley2400Serial


@dataclass(frozen=True)
class HardwarePreflightResult:
    port: str
    baud_rate: int
    idn: str
    output_off_confirmed: bool


def _output_is_off(raw: str) -> bool:
    value = str(raw).strip().upper()
    if value in {"OFF", "FALSE"}:
        return True
    try:
        return float(value) == 0.0
    except (TypeError, ValueError):
        return False


def run_keithley_preflight(
    port: str,
    baud_rate: int = 9600,
    *,
    logger: Callable[[str], None] | None = None,
) -> HardwarePreflightResult:
    """Minimal real-hardware safety preflight for Keithley 2400-family units.

    The preflight forces and verifies OUTPUT OFF before identity work. It never
    sources voltage/current or issues a measurement read.
    """

    def log(msg: str) -> None:
        if logger is not None:
            logger(msg)

    inst = Keithley2400Serial(port=port, baud_rate=baud_rate)
    connected = False
    idn = ""
    try:
        log(f"Opening serial port {port} at {baud_rate} baud")
        inst.connect()
        connected = True
        inst.output_off()
        output_state = inst.query(":OUTP?")
        if not _output_is_off(output_state):
            raise RuntimeError(
                f"Instrument reported output state {output_state!r} after OUTPUT OFF."
            )
        log(f"Output OFF verified by :OUTP? -> {output_state}")
        idn = inst.identify()
        log(f"*IDN? -> {idn}")
        return HardwarePreflightResult(
            port=port,
            baud_rate=baud_rate,
            idn=idn,
            output_off_confirmed=True,
        )
    finally:
        try:
            if connected:
                inst.output_off()
        finally:
            inst.close()
