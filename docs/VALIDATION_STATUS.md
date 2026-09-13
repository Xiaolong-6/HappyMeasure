# Current Validation Status

Release candidate: **HappyMeasure `1.1b6`**

This file records the current release gate. Historical implementation notes and superseded artifact measurements belong in Git history/release records, not here.

## Current decision

Status on 2026-09-13: **SOURCE READY**.

The automated source gate is green. Desktop/package smoke and staged real-hardware validation are still required before `v1.1b6` can be described as hardware-verified or released.

## Automated source gate

Required before hardware validation or tagging:

- Windows Python 3.11/3.12/3.13/3.14: compileall, Black, Ruff, mypy and core pytest.
- Python 3.14 core coverage: `>=95%`.
- Dedicated Windows/Python 3.12 Map Reconstruction job with `.[dev,map]`, PySide6/pyqtgraph import checks, mypy and the offscreen Qt release gate.
- Version/namespace/settings/export/safety regressions pass.

Audited green baseline on 2026-09-13:

- commit `19983f1` (`P1` release-correctness hardening);
- GitHub Actions run `34763860068`: all five jobs passed;
- Python 3.11, 3.12, 3.13 and 3.14 core jobs: pass;
- Python 3.14 core coverage: **95.04%** (required `>=95%`);
- Map Reconstruction Windows/Python 3.12 Qt gate: pass;
- hardware preflight parser/verification coverage: 100% in the coverage report.

`P2` is the release/audit closeout: operator safety wording, release documentation and regression checks. The **SOURCE READY** decision remains valid only while current `main`/HEAD CI stays green.

## Safety hardening included in this candidate

- `OUTPUT OFF` write failures from the real serial driver propagate instead of being silently converted into success.
- Hardware preflight sends `OUTPUT OFF`, queries `:OUTP?`, and requires a reported off state before passing.
- `READ?` is not automatically replayed after a timeout; the default serial timeout is bounded for stop responsiveness.
- STOP is explicitly cooperative: active serial I/O must return before software cleanup can complete. For immediate physical output-off, use the instrument front panel.
- Closing the main window during a run requests Stop and waits for cleanup instead of destroying the UI immediately.
- The first requested source setpoint is written before `OUTPUT ON`.
- Fixed source ranges reject requested setpoints outside the configured range before a run starts.
- Measurement failures can rescue already-acquired points into a partial trace/backup instead of discarding all collected data.
- Fast/Custom real-hardware acquisition remains capability-gated; the current release evidence is specifically for Keithley MODEL 2401.

## Desktop/package gate

Still requires operator verification on the actual Windows release candidate:

1. HappyMeasure launches at normal and short/low-resolution window sizes.
2. Settings developer section remains scrollable/reachable after UI Diagnostics.
3. Standard/Fast/Custom Constant-Time acquisition controls are readable and responsive.
4. Long live Time plot follows smoothly without axis flicker; completed trace can display the whole run.
5. Trace save/export names are readable and contain no duplicated tokens.
6. Map Reconstruction opens maximized; Restore gives a usable normal window.
7. CSV A -> reconstruct/analyse -> CSV B resets to the new source/workspace.
8. `.hmmap` save/open round-trip is coherent.
9. `Flip color`, manual min/max and percentile controls are visible and responsive.
10. Fresh Windows portable builds launch and simulator/package smoke succeeds.

Do **not** reuse the previously measured portable ZIP sizes/hashes as final evidence after source changes. Rebuild both packages from the final release commit and record the new size and SHA-256 in the final release record.

## Hardware gate

Automated tests do **not** certify real hardware.

Before publishing `v1.1b6`, follow `HARDWARE_VALIDATION_PROTOCOL.md` in order. Begin with no DUT/analog leads, run the output-off preflight, then the no-DUT 2401 smoke, then a known passive load before any real DUT.

At minimum confirm physical/front-panel `OUTPUT OFF` after:

- normal completion;
- STOP;
- Abort/error;
- disconnect;
- application close after an active run.

Fast/Custom cleanup contract: every run starts from instrument reset/configuration, so the next run is deterministic. Post-Fast cleanup normalizes operator-facing filter/autozero/display state and keeps output-off safety primary; it does not claim to restore an unknown arbitrary pre-run front-panel configuration.

## Release status vocabulary

- **SOURCE READY**: current automated core/Qt gates pass.
- **DESKTOP READY**: source gates plus local Windows UX/package smoke pass.
- **HARDWARE VERIFIED**: the selected staged real-hardware gate also passes with recorded evidence.
- **RELEASED**: tag/release/artifacts are published and post-release download/update checks pass.
