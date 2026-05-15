# Troubleshooting

Run diagnostics first:

```powershell
tools\diagnostics\Run_Diagnostics.bat
```

The report is written to:

```text
logs/diagnostics_report.txt
```

Useful logs:

```text
logs/log.txt
logs/error.log
logs/console_last_run.log
```

If the app cannot import `keith_ivt`, use `Run_HappyMeasure.bat`; it sets `PYTHONPATH=src`, quotes project paths with spaces, and attempts editable installation automatically. For paths such as `XX - YY UNIVERSITY`, prefer the updated root launchers or the updated scripts in `tools\...`; avoid manually typing unquoted paths.


### Windows build note: Python 3.14 / temp log PermissionError

The portable-app build scripts now reject stale or unsupported `.venv` environments and rebuild with Python 3.11-3.13. This avoids Windows `PermissionError: [WinError 32]` failures seen when Python 3.14 keeps temporary log files open during validation. If the build still fails, delete `.venv`, close any running HappyMeasure/Python windows, and rerun `tools\build\Build_Portable_Windows_App.bat`.


### Build launcher Python detection fix

The Windows portable build launcher now verifies actual interpreter availability before selecting `py -3.13` / `py -3.12` / `py -3.11`. If only Python 3.14+ is installed, the launcher attempts a fallback build and prints a warning; Python 3.12 remains the recommended release-build interpreter.
