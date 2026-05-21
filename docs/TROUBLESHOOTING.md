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


### Windows build note: Python versions and temp permissions

The standard portable-app build script rejects stale or unsupported `.venv`
environments and rebuilds with Python 3.12, 3.11, or 3.13. Python 3.14 uses the
dedicated `Build_Portable_Windows_App_Python314` script, skips full pytest
during packaging, and installs explicit dependencies with `PYTHONPATH=src`
instead of using editable install. This avoids temp-directory permission
failures seen with `pip install -e` on some Windows/Python 3.14 machines.


### Build launcher Python detection fix

The Windows portable build launcher now verifies actual interpreter
availability before selecting `py -3.12` / `py -3.11` / `py -3.13`. If only
Python 3.14 is installed, run
`tools\build\Build_Portable_Windows_App_Python314.bat` or the matching
PowerShell script.
