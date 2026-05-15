from __future__ import annotations

import argparse

from keith_ivt.services.hardware_preflight import run_keithley_preflight


def main() -> None:
    parser = argparse.ArgumentParser(description="HappyMeasure Keithley serial preflight: IDN + output-off only.")
    parser.add_argument("port", help="Serial port, e.g. COM3")
    parser.add_argument("--baud", type=int, default=9600, help="Baud rate, default 9600")
    args = parser.parse_args()
    result = run_keithley_preflight(args.port, args.baud, logger=print)
    print("PASS hardware preflight")
    print(f"Port: {result.port}")
    print(f"Baud: {result.baud_rate}")
    print(f"IDN: {result.idn}")
    print(f"Output OFF confirmed: {result.output_off_confirmed}")


if __name__ == "__main__":
    main()
