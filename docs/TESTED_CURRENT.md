# Current Test Status

## 2026-09-10 - Map workflow close-out and elapsed-time remediation

### Map Reconstruction validation

- Scoped Map Reconstruction gate: **151 passed**, using a repository-local
  pytest base temporary directory to avoid the Windows system-temp ACL issue.
- The Analysis workspace is now a horizontal controls/map/diagnostics splitter
  with a vertical Samples / pixel + Distribution diagnostics splitter. Focused
  regressions cover simultaneous diagnostics, usable region minima, one source
  of scientific state, distribution-only histogram controls, display-only
  colour limits, stage-local exports, repairable preparation errors, HTML
  reporting, and reversible palette inversion.
- Offscreen screenshots for all three stages at 1280×800, 1600×900, and
  1920×1000 showed the resizable regions without major clipping. The offscreen
  Qt font backend rendered text as glyph boxes, so this was layout-only review;
  no native desktop window was inspected.

### HappyMeasure validation

- Focused hardware/acquisition gate: **76 passed** (Fast profile, 2401
  connection/beep, SCPI command ordering, Constant-Time timing and pause,
  CSV round trips, range labels/telemetry wording, and front-panel contracts).
- `SweepRunner` now uses `time.perf_counter_ns()` for acquisition timestamps,
  deadline scheduling, and pause bookkeeping. CSV writes 17 significant
  elapsed-time digits; Data Table displays the same precision. Regression
  coverage preserves closely-spaced timestamps through HappyMeasure export,
  re-import, and Map Reconstruction import.
- A recognised Keithley overflow is omitted only from Constant-Time result
  points, recorded as an acquisition warning/CSV metadata, and followed by the
  next read; unrelated non-finite readback remains an error. Step/Adaptive
  behavior remains conservative.
- The operator, not this validation session, physically retested the Fast
  2401 V-source/current-measure SCPI sequence and reported normal current
  measurement without persistent `9.91E+37`.
- Ruff, Black, mypy, and compileall passed for all changed modules.

## 2026-09-10 - Fast Acquisition merge blockers (final)

### HappyMeasure validation

- Synced with latest main via `merge origin/main` (no conflicts); all
  Three-Stage Map Reconstruction files are byte-identical to main, and the
  Fast branch owns only `keith_ivt` acquisition/core/driver/UI paths plus its
  two Fast test modules.
- Focused Fast/Standard/Custom/runner/driver/metadata set: **161 passed**
  (fast profile + persistence, sweep safety, fault injection, sweep-controller
  recovery, pre-hardware safety, mock-VISA command sequence, import/export
  store, models/adaptive, hysteresis, delay timing, core coverage gaps,
  simulator behavior, continuous-time timing, pause/adaptive, presets,
  settings compatibility, plus the HappyMeasure CSV importer sanity check).
- Blocker #1 (AutoZero order): driver already sends
  `:SYST:AZER:STAT ONCE` → `*WAI` → `:SYST:AZER:STAT OFF`; the regression now
  asserts the exact contiguous subsequence, not just membership.
- Blocker #2 (source-write-once): `SweepRunner` owns per-sample source writes
  and `read_source_and_measure()` only reads; new regression runs Custom
  Constant Time with `source_write_each_sample=True` through the real driver
  class and proves 4 samples → 4 `:READ?` and exactly 5 `:SOUR:VOLT` writes
  (one pre-run set + one per sample: not zero, not two).
- Also repaired two main-era regressions the branch had broken: restored the
  historical `Duration must be finite.` / `Interval must be finite.` /
  `Interval must be positive.` / `Duration must be positive.` validation
  messages while keeping Fast interval exemption, and removed a surplus
  `:SENS:CURR:RANG?` query from `set_current_autorange` so the setter stays a
  single write.
- Fast hot path verified: source set once, then `:READ?` only; no per-sample
  range queries (cache-only with telemetry off); no baud change; `:FORM:ELEM
  CURR` with cached source value for V-source/I-measure; Standard keeps
  two-field readback and live telemetry; Step sweeps unchanged; Custom knobs
  honored exactly once with Custom → Fast → Custom snapshot restore.
- CSV provenance round-trips all acquisition flags; old files without the new
  fields load with historical defaults. Map importer sanity passes; no Map
  Reconstruction scientific file was modified.
- Ruff passes, Black passes, mypy passes (9 changed modules; two pre-existing
  branch-only findings annotated without runtime effect), and `compileall`
  passes for the touched sources and tests.
- Tk state smoke passes headless (Standard/Fast/Custom switching, Fast preset
  vars, Custom snapshot restore, non-Time fallback). Full-app visual layout
  check was not performed in this session.
- Real hardware: not tested. The ~14-16 ms/sample rate remains a
  benchmark note, not a guarantee.

### Map Reconstruction validation

- Not rerun beyond the HappyMeasure CSV importer sanity check; merge
  resolution left every Map Reconstruction scientific file identical to main.

## 2026-09-10 - Three-stage project merge-gate validation (final)

### Map Reconstruction validation

- Merge-gate project/archive focus: **25 passed**
  (`test_project_io.py` 17 + `test_three_stage_integration.py` 8), run with
  `--basetemp=.pytest_tmp_three_stage`. The previous Windows host
  temp-directory ACL (`WinError 5`) is resolved by the writable basetemp; the
  temp directory was removed after validation and not committed.
- Extended related set: **33 passed** (adds `test_exporting.py` +
  `test_preparation.py`).
- Full scoped Map Reconstruction run: **154 passed**
  (`tests/map_reconstruction` + `tests/test_map_distribution.py` +
  `tests/test_map_reconstruction_ui_regressions.py`).
- v1 parity: literal historical v1 states restore identity (`None`)
  preparation; Legacy method, geometry, timing, point offset, and map
  processing preserved; no dark correction introduced.
- v2 parity: literal historical v2 states restore identity preparation;
  Phase Window timing, Y phase, X offset/phase, window mode/width, and
  aggregation preserved.
- v3 round trip: constant, manual-region, and rolling-quantile preparation
  (including response direction, value gate, and output convention) plus
  signal, geometry, method, processing, and display state reproduce the same
  valid scientific state. Reconstruction mathematics is unchanged (no diff in
  `methods/` or `models.py`).
- Invalid preparation: repairable-workspace behavior holds — source data stays
  available, saved config stays explicit, `PreparedSignal`/`result`/`processed`
  stay unavailable, and no silent fallback to raw/previous baseline occurs
  (geometry change and invalid-gate regressions pass).
- Preparation `None` parity: identity copy is independent and numerically
  identical to the legacy raw path; SHA-256 source-integrity rejection and
  archive-member validation pass.
- Rolling-quantile polarity: negative photocurrent uses the upper dark
  envelope, positive uses the lower envelope; round trip preserves direction.
- Reporting/provenance: parameter summary and processed sidecar carry source
  signal, dark-correction mode, output convention, and mode-specific
  preparation detail without dumping raw arrays.
- Scoped `map_reconstruction` coverage for this Map-only run: **93.36%**.
  The repository 95% gate is the combined `keith_ivt` + `map_reconstruction`
  full-suite gate, so no meaningless tests were added to inflate this scoped
  number.
- Ruff passes for `src/map_reconstruction/` and `tests/map_reconstruction/`;
  Black passes for all changed Map Reconstruction modules; mypy passes for
  11 changed source files; `compileall` passes for `src/map_reconstruction`
  and the touched test modules.
- Offscreen Qt integration/UI regressions pass (fixtures force
  `QT_QPA_PLATFORM=offscreen`). Native desktop visual check was not performed
  in this session.
- Fixes in this pass (no scientific changes): synchronized the stale
  `test_exporting` fake window with the intended `signal_preparation` /
  `prepared_metadata` sidecar contract, removed one pre-existing unused
  `PreparedSignal` import flagged by Ruff, and applied repo-standard Black
  wrapping to two pre-existing long lines.

### HappyMeasure validation

- Not rerun; this branch changes only Map Reconstruction sources and optional
  project/UI components.

## 2026-09-10 - Three-stage Signal Preparation workspace

### Map Reconstruction validation

- The scoped Map Reconstruction run reports **105 passed, 7 deselected**,
  including **6 preparation tests** and **23 non-project UI regressions**.
  Project/archive tests are currently blocked by the host temporary-directory
  ACL (`WinError 5`) while pytest creates its `tmp_path` fixture.
- Offscreen Qt construction passed with the three-page stack at **1024×650**;
  the processing section is hosted by Analysis and the raw/prepared trace is
  hosted by Preparation.
- Ruff, Black, mypy, and `compileall` pass for the changed Map Reconstruction
  sources. Temporary synthetic screenshots for all three pages were generated,
  visually inspected, and removed.
- A partial focused coverage run reported 70%, but it is not a coverage gate:
  the full Map Reconstruction coverage run is blocked by the same host ACL.

### HappyMeasure validation

- Not rerun; this branch changes only Map Reconstruction sources and optional
  project/UI components.

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
