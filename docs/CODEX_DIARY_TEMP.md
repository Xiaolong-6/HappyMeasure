# Codex Diary (Temporary)

This temporary diary records changes made during Codex-assisted turns so release notes can be prepared later.

## 2026-05-16

### Public package namespace migration

- Promoted runtime `PACKAGE_NAME` from the legacy `keith_ivt` namespace to the public `happymeasure` namespace.
- Added `src/happymeasure` command wrappers for `python -m happymeasure`, `python -m happymeasure.hardware_preflight`, and `python -m happymeasure.diagnostics`.
- Kept the existing `keith_ivt` implementation package and imports as a compatibility layer, so old imports and fallback launch paths continue to work.
- Updated Windows launchers, PyInstaller entry points, README/docs, and namespace tests to prefer `happymeasure` while preserving `keith_ivt` fallback behavior.

### Stop / Abort / Pause safety hardening

- Hardened `SweepRunner` so an operator stop attempts `output_off()` even when `output_off_after_run=False`.
- Preserved the existing normal-completion behavior: a successful full sweep still respects `output_off_after_run=False`.
- Added safe output-off error handling so a failed output-off command does not hide the original measurement exception.
- Applied the same output-off error-preservation pattern to the newer `MeasurementService` boundary.
- Added `tests/test_sweep_safety.py` covering operator stop, normal completion, measurement exception cleanup, and output-off failure context.
- Added/updated agent-facing handoff context for the safety contract.
