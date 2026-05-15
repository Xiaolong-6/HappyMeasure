# Hardware validation protocol — HappyMeasure 0.7a1

This is a human bench protocol. Do not treat simulator, mock serial, or coverage success as proof of physical hardware safety.

## Required order

### Level 0 — No DUT connected

1. Connect only the Keithley 2400/2450 communication cable.
2. Run:

```text
tools\hardware\Real_Hardware_Preflight.bat
```

3. Confirm:
   - `*IDN?` returns the expected instrument.
   - `:OUTP OFF` is sent.
   - front/rear terminal selection is what the UI says.
   - no voltage/current is sourced.

### Level 1 — Dummy resistor

Use known resistors before any real device:

```text
1 kΩ
10 kΩ
1 MΩ
```

Suggested voltage-source check:

```text
-1 V to +1 V, step 0.25 V, current compliance 10 mA, NPLC 0.1 or 1
```

Expected result:

```text
I ≈ V / R
```

Abort/STOP once during this level and confirm output goes off.

### Level 2 — Diode or robust test device

Only after Level 1 passes:

```text
small voltage-source diode IV
small current-source diode IV
compliance-limited case
pause/resume/STOP case
partial-data save case
```

### Level 3 — Real DUT

Only after Level 2 passes. Save the CSV and the console/runtime logs for every first-run attempt.

## Pre-hardware software gates

Run before connecting a real DUT:

```text
python tests\run_full_validation.py
python -m pytest tests\test_pre_hardware_safety.py tests\test_mock_visa_command_sequence.py -q
```

These tests check software intent and output-off recovery paths. They do not verify actual relay state or analog output behavior.

## Record in handoff after bench validation

- Date/time.
- Operator.
- Keithley model and firmware.
- Serial/VISA resource.
- Front/rear terminal path.
- Sense wiring.
- Sweep mode and compliance.
- DUT/dummy load.
- Output-off behavior after complete, abort, exception, and close-window.
- CSV file name and log file names.
