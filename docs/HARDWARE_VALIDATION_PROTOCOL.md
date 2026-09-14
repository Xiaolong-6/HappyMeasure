# Hardware validation protocol — HappyMeasure

This document defines staged real-hardware validation. Simulator, mock serial, CI and coverage success do **not** prove physical hardware safety or analog accuracy.

## Safety rules

1. Set and independently verify compliance before enabling output.
2. Confirm the actual instrument model/firmware and its limits.
3. Confirm front/rear terminal selection and 2-wire/4-wire sense wiring.
4. Start from no-DUT communication before passive loads or devices.
5. If behavior is unexpected, use the instrument front panel to force output off.
6. After completion/Stop/Abort/error/disconnect/close, verify output is off whenever that path is part of the bench test.

## Level 0A — Built-in Hardware Diagnostics

Enable **Settings → Show developer tools** and choose **Run Hardware Diagnostics...**.

The diagnostic is intentionally narrow. It verifies communication/identity and output-off state behind an explicit no-DUT gate. It must not reset/configure the SMU, issue `READ?`, set a source value, start a measurement or enable source output.

## Level 0B — Repository preflight and no-DUT smoke

With analog terminals disconnected, run explicit serial preflight using the actual operator-selected COM and baud. See `HARDWARE_PREFLIGHT.md`.

The no-DUT smoke runner exercises communication, 0 V measurement/timing, pause/resume, Stop/restart and cleanup. Release mode on MODEL 2401 additionally exercises the validated Standard/Fast paths.

Example:

```powershell
.\.venv\Scripts\python.exe tools\hardware\keithley2400_smoke.py --port COM3 --baud 57600 --terminal rear --release
```

Change all bench-specific values to the actual instrument configuration. Do not commit the physical serial number or local result-folder paths.

## Level 1 — Known passive load

Optional deeper quantitative validation uses a known resistor with conservative source/compliance settings and compares `I ≈ V/R`. This level validates analog source/readback behavior more directly than no-DUT smoke.

Do not claim Level 1 evidence unless the physical load was actually connected and measured.

## Level 2 — Robust test device

Optional device-level validation may cover low-risk IV, current-source mode, compliance behavior, partial-data recovery/export and Standard/Fast comparison.

## Level 3 — Real DUT

Use only after the preceding safety/communication checks appropriate to the measurement risk. Start with conservative limits.

## Current release-line evidence

The current development line has already completed a real Keithley **MODEL 2401** no-DUT preflight and release-mode smoke. The retained evidence covers communication/control/timing/cleanup, including Standard, Fast fixed range, Fast Auto range, pause/resume, Stop/restart, SCPI ordering and output-off verification.

No passive-load quantitative test was performed in that session. Therefore the release claim must remain **2401 no-DUT communication/control verified**, not quantitative analog accuracy or arbitrary-DUT verified.

A new bench session is required before release only if subsequent source changes materially affect serial I/O, source-output safety, acquisition sequencing, compliance/range programming or cleanup behavior. Pure documentation/UI-display/package changes do not automatically invalidate the existing no-DUT evidence.

## Recording evidence

Release evidence should contain only what is needed to reproduce the test:

- date and git commit/build;
- instrument model/firmware family, without a physical serial number;
- selected COM/baud/terminal/wiring when relevant to the bench record;
- source/compliance/range/NPLC/profile;
- no-DUT/passive-load/test-device scope;
- output-off behavior and generated artifact names using relative/sanitized paths;
- warnings, overflow or throughput limitations.

Do not commit workstation usernames, absolute home-directory paths, or physical instrument serial numbers.
