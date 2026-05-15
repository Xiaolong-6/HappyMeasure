from __future__ import annotations

from keith_ivt.diagnostics.report import collect_diagnostics, write_diagnostics_report


def main() -> None:
    for check in collect_diagnostics():
        print(check.line())
    report = write_diagnostics_report()
    print(f"Diagnostics report written to: {report}")


if __name__ == "__main__":
    main()
