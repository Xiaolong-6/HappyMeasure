# Testing Strategy

## Current gates

```powershell
python tests/run_full_validation.py
python -m pytest -q
```

Optional desktop UI smoke:

```powershell
$env:HAPPYMEASURE_RUN_TK_SMOKE="1"
python -m pytest tests/test_ui_smoke.py -q
```

## Hardware gate before beta

- Real Windows Tk smoke test.
- Real serial preflight: `python -m keith_ivt.hardware_preflight COMx --baud 9600`.
- Dummy-load STEP sweep.
- Constant-time stop test.
- Error-path test with disconnected serial cable only after confirming output-off behavior on dummy load.

## Coverage note

The coverage configuration now includes `services/` and `drivers/` rather than omitting all of them. Hardware-only branches still need mock/fake serial coverage before beta.
