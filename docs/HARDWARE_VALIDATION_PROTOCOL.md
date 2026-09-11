# Hardware validation protocol — HappyMeasure 1.1b5

This is a human bench protocol. Do not treat simulator, mock serial, or coverage success as proof of physical hardware safety.

## Safety rules

1. Compliance is mandatory.
   - In voltage-source mode, compliance is current in amperes.
   - In current-source mode, compliance is voltage in volts.
2. Confirm the actual Keithley model limits before use.
3. Confirm front/rear terminal selection before enabling output.
4. Confirm 2-wire or 4-wire sense mode before measuring.
5. For high-impedance or insulating devices, use conservative current source and voltage compliance.
6. Run the simulator first, then a low-risk open-circuit hardware check.
7. If anything looks wrong, turn output off from the instrument front panel.

## Built-in Level-0 Hardware Diagnostics

For a quick communication/output-safety check, open **Settings**, enable
**Show developer tools**, and choose **Run Hardware Diagnostics...**.

The built-in diagnostic is deliberately narrower than the 0 V smoke runner.
It requires the debug simulator to be off, no active measurement, the normal
Hardware-page connection to be disconnected, and an explicit operator
confirmation that no DUT or analog test leads are connected. It then:

- sends `OUTPUT OFF` before other instrument actions;
- queries `*IDN?` and verifies a validated Keithley 2400-family identity;
- queries `:OUTP?` and requires output to report off;
- sends one short beep using the driver's state-preserving beep helper;
- closes and reopens the serial port; and
- verifies the same instrument and output-off state before final cleanup.

The built-in diagnostic never resets/configures the SMU, issues `READ?`, sets a
source value, starts a measurement, or enables source output. Serial work runs
off the Tk thread using a snapshot of the selected port and baud rate. Software
cannot hear the confirmation beep, so the operator must manually confirm that
exactly one short beep was audible.

Passing this check proves only the basic communication/output-off contract. It
does **not** replace the no-DUT 0 V smoke runner below, Fast release validation,
dummy-resistor testing, or real-DUT validation.

## No-DUT Keithley 2400/2401 smoke runner

For a safe open-circuit timing and lifecycle check after the simulator gates,
copy or use the repository-provided runner:

```bat
tools\hardware\Run_Keithley2400_Smoke.bat
```

Before starting, edit `PORT`, `BAUD`, and `TERMINAL` in the batch file if the
instrument is not on `COM3`, `57600`, and `rear`. The runner accepts Keithley
2400/2401-family IDs and deliberately uses only:

- voltage source at `0 V`;
- current measurement with a `100 µA` compliance;
- 2-wire sense;
- disconnected analog terminals / no DUT;
- output-off after every case.

Mode 1 QUICK covers IDN, confirmation beep, source-delay ownership, finite
0 V readback, four timing intervals, pause/resume rebase, and stop/restart.
Mode 2 FULL adds NPLC 1, more intervals, and fixed-versus-auto range-query
checks. Mode 3 adds the optional battery idle/sleep-prevention observation and
should only be run when an operator is ready to unplug AC and observe the
machine.

Each run writes `summary.txt`, `summary.json`, `timing_stats.csv`,
`runtime.log`, and raw point CSVs under `hardware_smoke_results\<timestamp>\`.
These local artifacts are intentionally ignored by Git.

### v1.2b1 Fast release block

For the Fast release contract, run the same script with `--release`:

```bat
.\.venv\Scripts\python.exe tools\hardware\keithley2400_smoke.py --port COM3 --baud 57600 --terminal rear --release
```

This adds, all at 0 V open-circuit unless noted: a short Standard run
(`standard.csv`), Fast fixed-range and Fast Auto-range runs
(`fast_fixed.csv`, `fast_auto.csv`), per-run timing/data-quality statistics
(mean/median/p95/min/max dt, effective rate, strictly-increasing check,
duplicate count, overflow count, non-finite count, warnings), a Fast SCPI
order check (`:SENS:FUNC:CONC OFF` before `:FORM:ELEM CURR`, no per-sample
range queries), and a bundle of `idn.txt`, `scpi_trace.txt`, and run metadata
(git commit, IDN, port/baud/terminal, source/compliance/NPLC/range/profile
settings) inside `summary.json`.

An optional Level-1 resistor comparison is available but never runs by
default:

```bat
... --release --resistor-ohms 10000
```

It sources 0.1 V (Standard and Fast) with 100 µA compliance, refuses to run
when the expected current is too close to compliance, and compares both
medians against `V/R` within `--resistor-tolerance` (default 20%). Ask the
operator for the resistor value when it is not supplied on the command line.

### 2026-09-08 no-DUT bench record

- Instrument: `KEITHLEY INSTRUMENTS INC., MODEL 2401`, firmware `B02 Jan 20 2021`.
- Mode 1 QUICK: PASS, including one physical confirmation beep and output-off
  after every case.
- Mode 2 FULL: PASS; fixed-range path made `0` range queries while auto-range
  made `66` queries.
- At NPLC 0.1, the observed readback floor was about `47 ms`; at NPLC 1 it
  was about `94–109 ms`. Requested `10–20 ms` intervals were classified as
  hardware/RS-232 throughput-limited, not as scheduler failures.
- Pause/resume rebase and immediate stop/restart both passed.
- Mode 3 battery sleep-prevention testing was intentionally not completed;
  it remains a separate operator-run check.

This record covers only the disconnected no-DUT smoke scope. It is not dummy
resistor, diode, real-DUT, or packaged-release validation.

## Required order

### Level 0 — No DUT connected: safety, timing, lifecycle

1. Connect only the Keithley 2400/2450 communication cable.
2. Run the built-in **Hardware Diagnostics** communication/output-off check
   when using the desktop UI.
3. Run:

```text
tools\hardware\Real_Hardware_Preflight.bat
```

4. Confirm:
    - `*IDN?` returns the expected instrument.
    - `:OUTP OFF` is sent.
    - front/rear terminal selection is what the UI says.
    - no voltage/current is sourced.
5. Run the `--release` smoke for the Fast release contract (Standard, Fast
   fixed-range, Fast Auto-range, pause/resume, stop/restart, SCPI order).

Fast acquisition is validated on the tested 2400-series hardware path,
specifically MODEL 2401 for the current release evidence. Untested 2450
support is not claimed: the app offers Fast/Custom only to validated
hardware, and the runner refuses other families for Fast runs.

Fast with Auto measurement range is allowed, but high-rate range transitions
are not monitored while live range telemetry is off. For quantitative
mapping work, use a fixed measurement range; the source range may remain
Auto.

### Level 1 — Dummy resistor: known passive load, functional comparison

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

Compare Standard and Fast measured current against the same expectation;
the `--resistor-ohms` runner mode automates this at 0.1 V.

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
