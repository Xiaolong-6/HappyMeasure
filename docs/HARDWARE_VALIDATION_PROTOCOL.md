# Hardware validation protocol — HappyMeasure 1.1b6

This is the human bench gate for a release candidate. Simulator, mock serial, CI, and coverage success do **not** prove physical hardware safety or analog correctness.

## Safety rules

1. Set and independently verify compliance before enabling output.
   - Voltage-source mode: compliance is current in amperes.
   - Current-source mode: compliance is voltage in volts.
2. Confirm the actual instrument model/firmware and its limits.
3. Confirm front/rear terminal selection and 2-wire/4-wire sense wiring.
4. Start with simulator/software gates, then no-DUT communication, then a known passive load, then a robust device, and only then a real DUT.
5. If behavior is unexpected, use the instrument front panel to force output off and stop the test.
6. After every completion/Stop/Abort/error/disconnect/close check, verify output is off.

## Level 0A — Built-in Hardware Diagnostics (no DUT, no analog test leads)

In HappyMeasure, enable **Settings → Show developer tools** and choose **Run Hardware Diagnostics...**.

The Run button must remain blocked unless:

- debug simulator is off;
- no measurement is active;
- the normal Hardware-page connection is disconnected;
- a COM port is selected; and
- the operator explicitly confirms that no DUT or analog test leads are connected.

The diagnostic is deliberately narrow:

1. send `OUTPUT OFF` before other instrument actions;
2. query `*IDN?` and validate the canonical model field;
3. query `:OUTP?` and require reported output-off state;
4. issue one short state-preserving confirmation beep;
5. close/reopen the serial connection;
6. verify the same identity and output-off state;
7. send `OUTPUT OFF` again before releasing each serial session.

It must not reset/configure the SMU, issue `READ?`, set a source value, start a measurement, or enable source output. The operator must manually confirm the audible beep; software cannot hear it.

Passing this proves only basic communication and output-off behavior.

## Level 0B — Repository preflight and no-DUT smoke

With analog terminals disconnected, run the repository preflight/smoke path from an operator-controlled Windows checkout. Configure COM port, baud and terminal for the actual instrument.

Preflight:

```text
tools\hardware\Real_Hardware_Preflight.bat
```

No-DUT smoke runner:

```text
tools\hardware\Run_Keithley2400_Smoke.bat
```

The no-DUT runner is intended to exercise communication, 0 V measurement/timing, pause/resume and stop/restart while preserving output-off cleanup. Inspect its generated `summary.txt`, `summary.json`, timing statistics, runtime log and raw point CSVs under the ignored local results directory.

For the `1.1b6` Fast acquisition gate, use the runner's release mode only on the validated model/context:

```text
.\.venv\Scripts\python.exe tools\hardware\keithley2400_smoke.py --port COM3 --baud 57600 --terminal rear --release
```

Change port/baud/terminal to the real bench configuration. The current release evidence validates Fast acquisition on **Keithley MODEL 2401**; simulator support and other 2400/2450-family identities are not evidence that Fast mode is validated on those physical models.

Release-mode checks should include:

- short Standard run;
- Fast fixed-range run;
- Fast Auto-range run if intentionally supported;
- timing/data-quality statistics;
- strictly increasing elapsed time;
- overflow/non-finite accounting;
- pause/resume rebase;
- immediate Stop/restart;
- SCPI ordering/no unintended per-sample telemetry;
- output off after every case.

For quantitative mapping/high-rate work, prefer a fixed measurement range. Auto measurement range is allowed only when its behavior is understood; live range telemetry is intentionally optional because extra serial queries affect throughput.

## Level 1 — Known passive load

Use a known resistor before a real device (for example 1 kΩ, 10 kΩ or 1 MΩ as appropriate for the compliance/range). Compare measured current with `I ≈ V/R` using conservative source values.

The smoke runner supports an optional resistor comparison, for example:

```text
... --release --resistor-ohms 10000
```

Do not run the resistor step unless the physical resistor is actually connected and the expected current is comfortably below compliance. Compare Standard and Fast results when validating Fast behavior.

During this level, exercise at least one Stop/Abort path and verify output off physically/front-panel-side afterward.

## Level 2 — Robust test device

Only after Level 1 passes, use a robust low-risk device and check:

- small voltage-source IV;
- small current-source IV where applicable;
- compliance-limited behavior;
- pause/resume and Stop;
- partial-data save/export;
- completed Time trace/full-history display;
- Standard/Fast comparison if Fast is in scope.

## Level 3 — Real DUT

Only after the earlier levels pass. Start with conservative limits and save the measurement CSV plus runtime/bench evidence for the first runs.

## Pre-hardware software gates

Before connecting a DUT, the source branch should already have passed CI. For a local checkout, useful focused checks include:

```text
python tests\run_full_validation.py
python -m pytest -q tests\happymeasure\test_pre_hardware_safety.py tests\happymeasure\test_mock_visa_command_sequence.py
```

These verify software intent and recovery paths only.

## Previous bench evidence

A 2026-09-08 no-DUT session on `KEITHLEY INSTRUMENTS INC., MODEL 2401`, firmware `B02 Jan 20 2021`, passed the then-current QUICK/FULL communication/timing checks, including confirmation beep, pause/resume rebase, stop/restart and output-off checks. At NPLC 0.1 the observed RS-232/readback floor was roughly 47 ms; at NPLC 1 it was roughly 94–109 ms.

This historical record is useful context but is **not** a substitute for the final `1.1b6` packaged-release/operator gate.

## Record for the current release

Record the final bench evidence in the release/validation record, not in a rolling agent diary:

- date/time and operator;
- git commit / candidate build;
- instrument model, firmware and IDN;
- serial resource, baud and terminal;
- sense wiring;
- measurement/profile/compliance/range/NPLC settings;
- no-DUT / resistor / test-device / DUT used;
- output-off behavior after complete, Stop, Abort/error, disconnect and close;
- produced CSV/log/smoke-result filenames;
- any warning, overflow or throughput limitation observed.

Only after the required stages pass should release notes use language such as hardware-verified.
