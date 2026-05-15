# HappyMeasure v0.7a1

First public alpha release candidate for HappyMeasure, a Windows desktop tool for Keithley 2400-series IV measurements.

## Highlights

- Windows portable build: unzip and run `HappyMeasure.exe`.
- Keithley 2401 serial hardware path verified on `COM3` at 9600 baud.
- Front-panel, 2-wire voltage-source/current-measure workflow tested with a high-value resistor.
- Conservative first-run hardware guidance included in the package.
- UI hover help clarified for START, PAUSE, and STOP:
  - START may turn real hardware output on after configuration.
  - PAUSE holds the current source/output state and does not turn output off.
  - STOP requests output off at the next safe point.
- Settings review dialog mouse-wheel handling fixed so closing the dialog does not leave a stale global binding.
- Public cleanup pass completed:
  - internal development cache/build folders excluded,
  - local `config/settings.json` removed,
  - documentation rule added to `CONTRIBUTING.md`.

## Hardware Validation Snapshot

Validated on 2026-05-15 with:

- Instrument: Keithley 2401
- Connection: Prolific PL2303 USB serial, `COM3`, 9600 baud
- Terminal: FRONT
- Sense: 2-wire
- Test load: high-value resistor on front panel
- Sweep: `-1 V` to `+1 V`, `0.25 V` step
- Result: approximately `148 MOhm`

Use the included `README_FIRST.txt` and `HARDWARE_VALIDATION_PROTOCOL.md` before connecting valuable devices.

## Download

Upload this asset to the GitHub Release:

- `HappyMeasure-0.7a1-windows-portable.zip`

Local build path:

- `C:\Users\liux16\my-app\HappyMeasure\release-clean\dist\HappyMeasure-0.7a1-windows-portable.zip`

## Known Notes

- This is an alpha release candidate intended for careful lab validation.
- Use conservative voltage/current limits for first hardware runs.
- PAUSE is not an output-off safety control; use STOP and confirm front-panel output state.
- Python 3.14 builds currently use the documented `.build-deps` PyInstaller workflow instead of a `.venv` workflow on this machine.

## Verification

- `python tests\test_legacy_ui_layout_contracts.py`
- `python -m compileall -q src tests`
- PyInstaller Windows folder build
- Packaged exe smoke test

