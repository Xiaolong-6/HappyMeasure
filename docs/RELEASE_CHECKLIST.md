# Release Checklist

## Source Tree

- Confirm no `__pycache__`, `.pytest_cache`, `.coverage`, `build`, `dist`,
  `logs`, or local backup files are present.
- Confirm `LICENSE` and `NOTICE.md` are present.
- Confirm README hardware warnings are current.
- Confirm the build script and build documentation target the same Python
  version.
- Confirm every behavior/build/UI/safety change has a matching documentation
  update, release-note/checklist entry, or an explicit "no docs needed" note.
- Confirm `CONTRIBUTING.md` still reflects the release workflow.

## Software Validation

Run from the repository root:

```powershell
python -m pip install -e ".[dev]"
python tests\run_full_validation.py
```

If Python 3.14 reports pycache permission errors on Windows, rerun with a
temporary cache prefix:

```powershell
$env:PYTHONPYCACHEPREFIX = Join-Path (Get-Location) ".pycache_tmp"
python tests\run_full_validation.py
```

## Hardware Validation

Follow `docs/HARDWARE_VALIDATION_PROTOCOL.md` in order:

- Level 0: communication cable only, no DUT.
- Level 1: dummy resistors.
- Level 2: diode or robust test device.
- Level 3: real DUT.

Record the instrument model, firmware, serial resource, terminal path, wiring,
compliance, output-off behavior, CSV files, and runtime logs.

## Packaging

Build the portable Windows folder app only after source validation passes:

```powershell
.\tools\build\Build_Portable_Windows_App.ps1
```

Distribute the whole `dist\HappyMeasure` folder, not only `HappyMeasure.exe`.

If PowerShell blocks unsigned scripts, run:

```bat
tools\build\Build_Portable_Windows_App.bat
```

If Python 3.14 `.venv` creation fails in `ensurepip`, use the local
`.build-deps` workaround in `docs\WINDOWS_PORTABLE_BUILD.md`.

Before release handoff:

- Confirm `dist\HappyMeasure\HappyMeasure.exe` exists.
- Confirm `dist\HappyMeasure\_internal` exists.
- Confirm `README_FIRST.txt`, `HARDWARE_VALIDATION_PROTOCOL.md`, and
  `HARDWARE_DRY_RUN_GUIDE.md` are copied into `dist\HappyMeasure`.
- Launch the packaged exe once and confirm it stays running.
- Zip the whole folder as `dist\HappyMeasure-0.7a1-windows-portable.zip`.
