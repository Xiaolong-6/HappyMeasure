# Current Test Status

## 2026-09-09 - Map Reconstruction audit remediation

The Map Reconstruction audit remediation and the existing HappyMeasure suite
passed through the full validation script:

```powershell
.\.venv\Scripts\python.exe tests\run_full_validation.py
```

Results:

- 605 tests collected; 604 passed and 1 expected conditional skip
- combined `keith_ivt` + `map_reconstruction` coverage gate passed
- compileall, legacy UI contracts, and the repository coverage gate passed
- Black, Ruff, source mypy, and map-package compile checks passed
- map UI regression tests cover synchronized signal switching, invalid-timing
  stale-state clearing, zero-valid-pixel empty state, point-period editing, and
  guide decimation, plus processing-only reuse of the raw reconstruction. The
  offscreen Qt smoke also rendered the revised layout.
- processing regressions cover explicit errors for degenerate normalization,
  physical versus dimensionless log10 labels, unitless custom/reference
  processing, and source/display unit separation in processed-export metadata.
- the supplied blue HappyMeasure and green Map Reconstruction icons are
  installed in their respective PNG/ICO asset pairs and the portable
  HappyMeasure packaging declaration still points at the HappyMeasure icon.
- the first full-suite attempt had one timing-sensitive PlotOptimizer failure;
  the immediate rerun passed completely
- no private source data, paths, metadata values, or observations were used or
  committed during this remediation

## 2026-09-07 - HappyMeasure 1.1b5 release candidate

The repository release-validation script passed using Python 3.12.10:

```powershell
.\.venv\Scripts\python.exe tests\run_full_validation.py
```

Results:

- compileall and legacy UI contracts passed
- full suite: 501 passed, 1 expected conditional skip
- core/hardware coverage: 95.14% (required minimum 95%)
- automated desktop simulator user-flow smoke test passed
- Ruff and source mypy checks passed in the available Python 3.12 environment

The standard PowerShell portable build completed with PyInstaller 6.22.2. The
required executable, `_internal`, first-run guide, hardware guides, config, and
example files were verified in both the folder and ZIP. `HappyMeasure.exe`
remained running during a five-second packaged startup smoke and was then
closed cleanly by the test process.

Current candidate artifact:

```text
HappyMeasure-1.1b5-windows-portable.zip
45,249,186 bytes
SHA-256 a4e51d1fc3871ed5f567cc1d1597526d3b58cd21aec6a7667e4dc307ee15df5e
```

The final `1.1b4` package passed the short real-hardware release gate. Repeat
that gate for `1.1b5` before describing this candidate as hardware-verified.

## Previous 1.1b4 validation

## 2026-07-23 - current desktop validation

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=keith_ivt --cov-report=term -q
```

Result: full suite passed with 1 expected skip. Coverage: 95.35%.

The Python 3.12 portable build reran the suite after the release-prep changes:
467 passed and 1 expected skip.

Full validation command:

```powershell
.\.venv\Scripts\python.exe -m pytest --tb=short -q
```

All tests pass. Coverage meets the 95% threshold for the unit-testable core/hardware subset.

Desktop user-flow validation command:

```powershell
.\.venv\Scripts\python.exe tests\run_ui_user_flow.py
```

This interactive smoke test uses only the Debug Simulator and temporary files.
It covers every navigation page, responsive window sizes, Light/Dark/Debug
themes, Step/Time/Adaptive sweeps, Pause/Resume/STOP, expected validation
errors, CSV import/export, PNG export, and Preset save/load round trips.

The `1.1b4` Windows portable folder and ZIP were then built successfully. The
required packaged files were verified, and `HappyMeasure.exe` opened a
responsive `HappyMeasure 1.1b4` window and closed normally.

The operator then confirmed the short real-hardware release gate using the
final packaged executable.

Final candidate artifact:

```text
HappyMeasure-1.1b4-windows-portable.zip
45,058,322 bytes
SHA-256 f19fc1ec4a2c7257c8508056df4102c59842a353d589ca0d79de1521f77318cb
```

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
