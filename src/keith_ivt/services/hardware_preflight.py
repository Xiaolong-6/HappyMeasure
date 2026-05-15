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


def run_keithley_preflight(
    port: str,
    baud_rate: int = 9600,
    *,
    logger: Callable[[str], None] | None = None,
) -> HardwarePreflightResult:
    """Minimal real-hardware safety preflight for Keithley 2400-family units.

    This intentionally does not source voltage/current.  It opens the serial
    port, queries *IDN?, sends output OFF, then closes the port.  Use it before
    the first real sweep after installing/updating HappyMeasure.
    """

    def log(msg: str) -> None:
        if logger is not None:
            logger(msg)

    inst = Keithley2400Serial(port=port, baud_rate=baud_rate)
    output_off = False
    try:
        log(f"Opening serial port {port} at {baud_rate} baud")
        inst.connect()
        idn = inst.identify()
        log(f"*IDN? -> {idn}")
        inst.output_off()
        output_off = True
        log("Output OFF command sent successfully")
        return HardwarePreflightResult(port=port, baud_rate=baud_rate, idn=idn, output_off_confirmed=output_off)
    finally:
        try:
            if not output_off:
                inst.output_off()
        finally:
            inst.close()
