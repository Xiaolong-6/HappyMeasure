# Current Test Status

## 2026-09-10 - Map Reconstruction final merge-blocker remediation

### Map Reconstruction validation

- 139 passed, 0 skipped across Map Reconstruction core, importer, processing,
  project, Distribution, and offscreen UI regressions.
- `map_reconstruction` coverage: **95.27%** (required minimum: 95%).
- The focused Distribution/UI regression set passed: 40 tests, including
  display-only color-limit metadata synchronization and excessive Count/Width
  histogram-bin rejection.
- Ruff, Black, mypy, and `compileall` passed for the changed Map
  Reconstruction sources.
- Histogram Count and Width requests share a 10,000-bin safety maximum; the
  existing Distribution error view handles rejected Width requests.

### HappyMeasure validation

- Not rerun; this remediation changes no shared hardware/acquisition,
  packaging, dependency, or release files.

## 2026-09-10 - Map Reconstruction analysis workspace

### Map Reconstruction validation

- 137 passed, 0 skipped: Map Reconstruction core, importer, processing,
  project, Distribution, and offscreen UI regressions.
- `map_reconstruction` coverage: **95.24%** (required minimum: 95%).
- Ruff, Black, mypy, and `compileall` passed for every changed Map
  Reconstruction source module.
- Offscreen Qt smoke passed at 1280×820 and 1024×650; the compact inspector
  retains its primary controls without a horizontal scrollbar at the narrower
  size.
- Native visual inspection was not performed: the desktop automation surface
  exposed no standalone application window in this session.

### HappyMeasure validation

- Not a validation gate for this Map Reconstruction-only branch; no shared
  hardware/acquisition, packaging, dependency, or release files changed.
- One exploratory whole-repository run observed the existing timing-sensitive
  `TestPlotOptimizer.test_frame_rate_limiting` failure. It is outside this
  branch's scope and was not used to validate or reject this change.

## 2026-09-09 - Dual Offset — Phase Window

- 654 tests collected; 653 passed and 1 expected conditional skip. The final
  full validation script passed with combined `keith_ivt` +
  `map_reconstruction` coverage of **95.10%**.
- Focused coverage includes period derivation, independent Y/X phase,
  canonical fractional phases, fraction/fixed windows, `[start, end)` sample
  selection, mean/median aggregation, empty windows as `NaN`/zero samples,
  scan orientation, fit validation, and Legacy conversion parity.
- Project tests cover unchanged v1 loading plus explicit v2 Phase Window
  registration round trips. Qt regressions cover method selection, band and
  used-sample overlay updates, sampling QC, and explicit Legacy conversion.
- Ruff, Black, compileall, and mypy for changed Map Reconstruction sources
  passed. Native drag and visual legibility review remain operator checks.

## 2026-09-09 - Map Reconstruction PDF partial-NaN rendering

- 637 tests collected; 636 passed and 1 expected conditional skip in the full
  validation script.
- Full validation passed, including compileall and the 95% coverage gate:
  combined `keith_ivt` + `map_reconstruction` coverage was **95.18%**.
- 35 focused project/report/UI regressions passed. They now include a direct
  `_array_image()` regression for partial-NaN maps plus raw-fallback and
  configured-processed PDF generation with finite and NaN pixels.
- Report rendering now indexes the LUT only with finite scientific values;
  invalid pixels remain the neutral gray report color and source arrays are
  not mutated.
- Ruff, Black, mypy for `reporting.py`, and compileall passed.
- Native Windows PDF viewer verification remains unavailable in this session;
  the offscreen Qt font backend still renders glyphs as boxes, so native PDF
  typography remains an operator verification step.

## 2026-09-09 - Map Reconstruction PDF orientation and color semantics

- 634 tests collected; the final full validation script completed successfully.
- 32 focused project/report/UI regressions passed, including display-only Flip
  Y for map and sample counts, Manual/Percentile color limits, raw fallback
  color-range isolation, and non-mutation of scientific arrays.
- Native Windows PDF viewer verification remains unavailable in this session.
  The offscreen Qt font backend still renders glyphs as boxes, so it cannot be
  used to verify native Unicode typography; Unicode strings remain unmodified.

## 2026-09-09 - Map Reconstruction restore and report remediation

- 633 tests collected; the final full validation script completed successfully.
- 31 focused project-persistence and Map Reconstruction UI regressions passed,
  including Voltage_V scientific-value restoration, raw-map PDF fallback,
  all-NaN processed fallback, aspect-fit helpers, Unicode source text, and
  non-mutating report generation.
- Ruff, Black, compileall, and mypy for the changed Map Reconstruction modules
  passed.
- The rendered offscreen Qt PDF preserves map/sample-count aspect ratio, but
  this environment's offscreen Qt font backend renders all glyphs as boxes
  (also reproduced by an isolated font probe). Native desktop PDF text and
  Unicode display therefore remain an operator verification step.

## 2026-09-09 - Map Reconstruction portable projects and reports

- 628 tests collected; the full validation script completed successfully with
  the combined coverage gate at 95.10% (required minimum: 95%)
- 26 focused project-persistence and map-UI regressions passed. They cover
  byte-preserving `.hmmap` archives, SHA-256 and malformed-archive rejection,
  full and partial project-state restoration, exactly one reconstruction on
  restore, action availability, parameter summaries, and non-mutating PDF
  generation.
- `compileall`, Ruff, per-file Black, and mypy for all changed Map
  Reconstruction source modules passed.
- The PDF test verifies a non-empty PDF with a valid header. This headless
  session could not perform a native PDF-viewer legibility review; that visual
  check, along with native file-dialog and mouse-interaction checks, remains
  an operator task.

## 2026-09-09 - Map Reconstruction compact timing workspace

- 616 tests collected; 615 passed and 1 expected conditional skip
- full validation passed with 95.56% combined `keith_ivt` +
  `map_reconstruction` coverage; compileall and legacy UI contracts passed
- Ruff, per-file Black, and mypy for the modified map UI source files passed
- 13 focused Qt UI regressions passed, including unset geometry, automatic
  trace-fitting anchors, protected manual anchors, action-specific export
  availability, compact timing precision, and processing-only error recovery
- `python -m map_reconstruction` was launched, but this session did not expose
  its native desktop window to the automation surface. Native drag, pan, zoom,
  resize, and file-dialog interactions therefore remain operator visual checks.

## 2026-09-09 - Map Reconstruction UI state remediation

- 611 tests collected; 610 passed and 1 expected conditional skip
- full validation passed with 95.56% combined `keith_ivt` +
  `map_reconstruction` coverage
- compileall, legacy UI contracts, Ruff, and per-file Black checks passed
- the synthetic single-v2 `load_file()` regression verifies trace-relative
  anchors, positive point period, and a valid reconstructed result
- the Qt UI regression verifies processing-only failure preserves raw result,
  Samples / pixel data, timing state, and raw export, then restores processed
  map and Distribution after the setting is fixed
- optional GUI dependencies were installed with `pip install -e ".[map]"`;
  offscreen `python -m map_reconstruction` launch and synthetic load probe
  passed, including both QC tabs and seconds-labelled point period
- changed `inspector.py` passes mypy. Repository-wide mypy still reports
  pre-existing typing errors in unrelated tests; no new source error remains.
- Native desktop visual interactions (drag completion, pan, wheel zoom, and
  1024×650 resize) were not manually verified in this headless session.

## 2026-09-09 - Constant Time duration-row state

- 608 tests collected; 607 passed and 1 expected conditional skip
- focused duration-row regressions cover finite mode, Until Stop disabling of
  both label and entry, value preservation, and Time → Step → Time rebuilding
- the existing Debug simulator desktop flow passed, and an actual Tk Debug
  probe confirmed the enabled/disabled states and preserved `123.45` duration
  across toggle and dynamic rebuild
- full validation passed with 95.56% coverage; compileall, Ruff, source mypy,
  and Black formatter checks passed

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
