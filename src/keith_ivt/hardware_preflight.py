from __future__ import annotations

import argparse
import sys

from keith_ivt.services.hardware_preflight import run_keithley_preflight
from keith_ivt.services.serial_discovery import discover_supported_serial_hardware

PREFLIGHT_SAFETY_NOTE = (
    "Safety: automatic COM discovery, when used, probes detected COM ports only at the "
    "selected --baud and sends *IDN? only. HappyMeasure never auto-scans alternate baud "
    "rates. The preflight then forces and verifies OUTPUT OFF; it does not source "
    "voltage/current, issue READ?, or run a sweep."
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="HappyMeasure Keithley serial preflight: COM discovery + output-off verification.",
        epilog=PREFLIGHT_SAFETY_NOTE,
    )
    parser.add_argument(
        "port",
        nargs="?",
        help=("Serial port, e.g. COM3. Omit to scan detected COM ports at the selected --baud."),
    )
    parser.add_argument("--baud", type=int, default=9600, help="Baud rate, default 9600")
    parser.add_argument(
        "--auto",
        action="store_true",
        help=(
            "Auto-detect a supported Keithley COM port using the selected --baud only. "
            "Alternate baud rates are never scanned."
        ),
    )
    args = parser.parse_args(argv)

    print(PREFLIGHT_SAFETY_NOTE)
    port = args.port
    baud = int(args.baud)

    if args.auto or not port:
        match = discover_supported_serial_hardware(
            preferred_port=port,
            preferred_baud=baud,
        )
        if match is None:
            print("FAIL hardware preflight")
            print(f"Reason: no supported Keithley 2400-family instrument responded at {baud} baud")
            print(
                "Action: keep the instrument output off, verify the Windows COM port and the "
                "instrument RS-232 baud setting, then retry with --baud or specify COM manually."
            )
            return 1
        port = match.port
        print(f"Auto-detected Keithley {match.model} on {port} at selected baud {baud}")

    assert port is not None
    try:
        result = run_keithley_preflight(port, baud, logger=print)
    except Exception as exc:
        print("FAIL hardware preflight")
        print(f"Port: {port}")
        print(f"Baud: {baud}")
        print(f"Reason: {exc}")
        print(
            "Action: keep the instrument output off, verify cabling/resource name and baud, "
            "then retry preflight before any real sweep."
        )
        return 1

    print("PASS hardware preflight")
    print(f"Port: {result.port}")
    print(f"Baud: {result.baud_rate}")
    print(f"IDN: {result.idn}")
    print(f"Output OFF confirmed: {result.output_off_confirmed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
