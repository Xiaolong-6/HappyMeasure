# Current Test Status

## 2026-07-23 - current desktop validation

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=keith_ivt --cov-report=term -q
```

Result: full suite passed with 1 expected skip. Coverage: 95.35%.

Full validation command:

```powershell
.\.venv\Scripts\python.exe -m pytest --tb=short -q
```

All tests pass. Coverage meets the 95% threshold for the unit-testable core/hardware subset.

Desktop user-flow validation command:

```powershell
.\.venv\Scripts\python.exe tests\run_ui_user_flow.py
```

This interactive smoke test uses only the Debug Simulator and temporary files.
It covers every navigation page, responsive window sizes, Light/Dark/Debug
themes, Step/Time/Adaptive sweeps, Pause/Resume/STOP, expected validation
errors, CSV import/export, PNG export, and Preset save/load round trips.

## Key coverage numbers for target files

| File | Coverage |
|---|---|
| `core/current_range.py` | 99% |
| `data/presets.py` | 100% |
| `drivers/keithley2400_adapter.py` | 100% |
| `services/update_installer.py` | 98% |

## Notes

- The system Python did not have `pytest`; use the project `.venv` Python shown above.
- Hardware preflight, diagnostics, UI modules, sweeps, adaptive logic, importers, logging config, app config, and `__main__` are omitted from coverage and handled by smoke/bench protocols.
