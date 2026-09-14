# Current Validation Status

This file records the validation scope that applies to the current development HEAD. The authoritative automated result is the GitHub Actions status for that exact commit; do not copy old run IDs forward as though they validate newer source.

## Current release-prep decision

The development line is in **release audit**. Publication requires the release CI gate to be green on the final selected commit and the Windows portable packages to be rebuilt from that same commit.

## Automated source gate

Required for release:

- Windows Python 3.11/3.12/3.13/3.14: compileall, Black, Ruff, mypy and core pytest;
- Python 3.14 configured core coverage `>=95%`;
- dedicated Windows/Python 3.12 Map Reconstruction job with real PySide6/pyqtgraph dependencies and offscreen Qt tests;
- per-commit internal version sequence check;
- repository privacy regression preventing workstation-specific home paths and known real instrument serial identifiers from returning;
- version/namespace/settings/export/safety regressions.

A green CI badge validates source behavior only. It does not validate a packaged EXE or quantitative analog performance.

## Real-hardware evidence retained for this release line

A real **Keithley MODEL 2401** no-DUT session on Windows passed the release smoke path with the instrument configured at the operator-selected serial settings. The physical serial number is intentionally not stored in the repository.

Verified scope included:

- explicit serial preflight;
- `OUTPUT OFF` command and `:OUTP? -> 0` verification;
- valid MODEL 2401 `*IDN?` response;
- no-DUT 0 V runs;
- Standard acquisition;
- Fast fixed-range acquisition;
- Fast Auto-range acquisition;
- pause/resume without catch-up behavior;
- Stop followed by immediate restart;
- SCPI ordering / no unintended hot-path range polling;
- output-off cleanup after the exercised cases.

No passive-load resistor test was performed in this release-prep session. Therefore the repository must **not** claim quantitative source/readback accuracy, calibrated resistance accuracy, arbitrary DUT validation, or physical validation of every supported 2400-family model. Additional hardware testing is optional for this release unless later code changes materially alter hardware I/O/safety behavior.

## Desktop/package gate

Before publication, rebuild both portable packages from the final selected commit and verify:

1. HappyMeasure launches and closes cleanly on Windows;
2. Settings/Developer Tools remain reachable and repeatable;
3. live Time history can switch between All data and Last N during a run without truncating saved data;
4. trace save/export/import works;
5. Map Reconstruction launches and performs a minimal CSV/project round-trip;
6. packaged artifact names, sizes and SHA-256 values are recorded in the final release record;
7. no logs, caches, local absolute paths, hardware-smoke result folders or local user data are packaged unintentionally.

## Status vocabulary

- **SOURCE READY** — automated source/Qt/version/privacy gates pass on the exact commit.
- **PACKAGE READY** — source gate plus fresh Windows package smoke passes.
- **2401 NO-DUT VERIFIED** — the recorded communication/control/safety smoke above passed; this is deliberately narrower than analog/DUT validation.
- **RELEASED** — a human selected the public version, tag/release/artifacts were published, and post-release download/update checks passed.
