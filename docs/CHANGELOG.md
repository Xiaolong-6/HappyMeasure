# Changelog

This file is intentionally concise. Git history preserves implementation detail; `RELEASE_NOTES_NEXT.md` is the current release draft.

## Unreleased — release-prep hardening

- Made serial detection COM-focused and removed automatic baud scanning from the GUI workflow.
- Fixed hardware-preflight circular import startup failure.
- Moved hardware diagnostics under Developer Tools and hardened diagnostic/settings page rebuild behavior.
- Fixed Default Settings review when application-only preferences have no dedicated Tk variable.
- Added persistent automatic-backup and log-recording preferences, defaulting to enabled.
- Added live Time-history controls that can switch All data / Last N points while acquisition is running without truncating scientific data.
- Cleaned stale documentation, removed workstation-specific path/serial identifiers, and added repository privacy/version-policy enforcement.
- Adopted per-commit internal beta serial increments; public release identity remains a human release decision.

## 1.1b6 — Time acquisition, Map Reconstruction, diagnostics and release hardening

- Added live-only Time plot history/marker/refresh policies and extrema-preserving display reduction for large completed traces.
- Added Standard/Fast/Custom Constant-Time acquisition profiles and related throughput controls.
- Added Windows power guard and safe hardware/UI diagnostics with output-off/no-DUT semantics.
- Reorganized Settings/developer controls and fixed update-check preference round-trip.
- Fixed automatic export naming for underscore-containing trace names and duplicated Time/Adaptive metadata.
- Added staged Signal Preparation → Reconstruction → Map Analysis, processing/color controls and self-contained `.hmmap` projects.
- Added dedicated Windows/Python 3.12 offscreen Qt Map Reconstruction CI gate and standalone portable packaging.

## 1.1b5 — Sweep direction and recovery hardening

- Step and Adaptive step values became magnitudes; Start/Stop determine direction.
- Added canonical preflight validation for active sweep values and non-finite input.
- Made runtime sweep errors recover to a reusable connected state while preserving output-off safety.

## 1.1b4 — Adaptive editor and exact presets

- Added multiline Adaptive segment editing and duplicate-value control.
- Presets restore visible Hardware + Sweep state accurately.
- Fixed retry-at-same-setpoint behavior after range-change discard and settings/import robustness issues.

## 1.1b3 — Front-panel range control

- Added current autorange/fixed-range control, settling/discard behavior and front-panel range status.
- Added Keithley range-query/timing regressions.

## 1.1b2 — Hysteresis sweep beta

- Added optional forward/reverse Step and Adaptive sweeps without duplicating the turn point.
- Preserved hysteresis metadata through CSV import/export.

## 1.1b1 — Startup updater beta

- Added startup update checking and portable-update handoff.
- Added plot panning/hover readout, auto-open front panel and per-point Delay control.

## 1.0b1 — Beta baseline

- Consolidated HappyMeasure public naming and compatibility namespace.
- Hardened state/recovery/output-off behavior and core trace workflows.

## Earlier alpha history

See Git tags/history for the pre-beta architecture and hardware-validation transition.
