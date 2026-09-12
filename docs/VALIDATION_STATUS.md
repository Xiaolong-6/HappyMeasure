# Current Validation Status

Release candidate: **HappyMeasure `1.1b6`**

This file records only the current gate. Historical test counts belong in Git history and release notes.

## Automated source gate

Required before merge/tag:

- Python 3.11/3.12/3.13/3.14 Windows CI: compileall, Black, Ruff, mypy, full pytest.
- Python 3.14 core coverage: `>=95%`.
- Dedicated Windows/Python 3.12 Map Reconstruction job with `.[dev,map]` and `QT_QPA_PLATFORM=offscreen`.
- Map job explicitly imports PySide6 and pyqtgraph before tests so missing Qt cannot appear as a successful all-skipped job.
- Version/namespace/settings/export/safety regressions pass.

Status on creation of the `1.1b6` hardening branch: **pending CI run**. The local
results below were refreshed on 2026-09-12; they do not claim CI completion.

## Local automated source gate (operator machine, Python 3.12.10)

Run on `codex/release-1.1b6-hardening` before release packaging:

- `tests/common` + `tests/happymeasure`: **0 failed** (494 collected;
  6 Tk smoke tests are skipped unless `HAPPYMEASURE_RUN_TK_SMOKE=1`).
- Core coverage (`keith_ivt`): **95.12%** (gate `>=95%`).
- Map Reconstruction gate with real Qt (`PySide6 6.11.2`, `QT_QPA_PLATFORM=offscreen`,
  zero skips): **175 passed**.
- `compileall`, Black, Ruff, mypy (`src/keith_ivt`, `src/happymeasure`,
  `src/map_reconstruction`): pass.
- Tk smoke with `HAPPYMEASURE_RUN_TK_SMOKE=1`: **6 passed**; the focused stale
  Constant-Time widget regression also passes.
- `tests/run_full_validation.py`: **pass** after keeping Map as an independent
  Qt gate and scoping the `>=95%` coverage threshold to core.
- Existing packaged executables: `HappyMeasure.exe` and `MapReconstruction.exe`
  each launched and stayed alive for 5 seconds, then were closed. A relative
  path scan of the Map bundle found no `keith_ivt`, `serial`, or `tkinter`
  package tree.
- Existing ZIP evidence: `HappyMeasure-1.1b6-windows-portable.zip` is 46,456,082
  bytes (`SHA-256 211B1337035906B0B60C6BC1D3CBC5F36D2BD030CC80F1C88E27CA075259BB8B`);
  `MapReconstruction-1.1b6-windows-portable.zip` is 277,356,207 bytes
  (`SHA-256 8642ABD66500901A7D2D1DA3D4090B10D48F589E19ACE36118606D945559D59A`).

Local result: **SOURCE READY** (operator desktop UX list, CI matrix, and
hardware gate still pending below).

## Desktop gate (operator machine)

Still requires local Windows verification after pulling the hardening branch:

1. HappyMeasure launches at normal and short/low-resolution window sizes.
2. Settings developer section remains scrollable/reachable after UI Diagnostics.
3. Standard/Fast/Custom Constant-Time acquisition controls are readable and responsive.
4. Long live Time plot follows smoothly without axis flicker; completed trace can display the whole run.
5. Trace save/export names are readable and contain no duplicated tokens.
6. Map Reconstruction opens maximized; Restore gives a usable normal window.
7. CSV A → reconstruct/analyse → CSV B correctly resets to the new source/workspace.
8. `.hmmap` save/open round-trip is coherent.
9. `Flip color`, manual min/max and percentile controls are visible and responsive.
10. Windows portable build launches and simulator smoke succeeds.

## Hardware gate

Automated tests do **not** certify real hardware.

Before publishing `v1.1b6`, follow `HARDWARE_VALIDATION_PROTOCOL.md`. At minimum repeat the safe 2401 no-DUT/0 V smoke and then the chosen dummy-load/DUT gate. Confirm `OUTPUT OFF` after completion, Stop, Abort, disconnect and error paths.

Fast/Custom cleanup contract: a run always starts with instrument reset/configuration, so the next run is deterministic. Post-Fast cleanup normalizes operator-facing filter/autozero/display state and always keeps output-off safety primary; it does not claim to restore an unknown arbitrary pre-run front-panel configuration.

## Release status vocabulary

- **SOURCE READY**: automated source/Qt gates pass.
- **DESKTOP READY**: source gates plus local Windows UX/package smoke pass.
- **HARDWARE VERIFIED**: staged hardware gate also passes.
- **RELEASED**: tag/release/artifact are published and post-release download/update checks pass.
