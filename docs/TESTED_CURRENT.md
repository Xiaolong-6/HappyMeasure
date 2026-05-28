# Current Test Status

## 2026-05-28 - Keithley current range front-panel control

Validated with the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_current_range_control.py tests\test_mock_visa_command_sequence.py tests\test_simulator_behavior.py -q -p no:cacheprovider
```

Result: 12 passed.

Notes:

- The system Python did not have `pytest`; use the project `.venv` Python shown above.
- The sandbox blocked pytest temp-directory cleanup when using `tmp_path`, so the new CSV filtering test writes its temporary CSV under ignored `logs/`.
