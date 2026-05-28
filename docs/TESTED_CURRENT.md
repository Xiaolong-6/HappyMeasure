# Current Test Status

## 2026-05-28 - v1.1b3 release validation

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=keith_ivt --cov-report=term -q
```

Result: 406 passed, 1 skipped. Coverage: 95.06%.

Full validation command:

```powershell
.\.venv\Scripts\python.exe -m pytest --tb=short -q
```

Result: 406 passed, 1 skipped.

All tests pass. Coverage meets the 95% threshold for the unit-testable core/hardware subset.

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
