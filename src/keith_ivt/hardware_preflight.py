from __future__ import annotations

import argparse
import sys

from keith_ivt.services.hardware_preflight import run_keithley_preflight


PREFLIGHT_SAFETY_NOTE = (
    "Safety: this preflight queries *IDN? and sends OUTPUT OFF only; "
    "it does not source voltage/current or run a sweep."
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="HappyMeasure Keithley serial preflight: IDN + output-off only.",
        epilog=PREFLIGHT_SAFETY_NOTE,
    )
    parser.add_argument("port", help="Serial port, e.g. COM3")
    parser.add_argument("--baud", type=int, default=9600, help="Baud rate, default 9600")
    args = parser.parse_args(argv)

    print(PREFLIGHT_SAFETY_NOTE)
    try:
        result = run_keithley_preflight(args.port, args.baud, logger=print)
    except Exception as exc:
        print("FAIL hardware preflight")
        print(f"Port: {args.port}")
        print(f"Baud: {args.baud}")
        print(f"Reason: {exc}")
        print("Action: keep the instrument output off, verify cabling/resource name, then retry preflight before any real sweep.")
        return 1

    print("PASS hardware preflight")
    print(f"Port: {result.port}")
    print(f"Baud: {result.baud_rate}")
    print(f"IDN: {result.idn}")
    print(f"Output OFF confirmed: {result.output_off_confirmed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
