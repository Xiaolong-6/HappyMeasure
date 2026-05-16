# Codex Diary (Temporary)

This temporary diary records changes made during Codex-assisted turns so release notes can be prepared later.

## 2026-05-16

### Public package namespace migration

- Promoted runtime `PACKAGE_NAME` from the legacy `keith_ivt` namespace to the public `happymeasure` namespace.
- Added `src/happymeasure` command wrappers for `python -m happymeasure`, `python -m happymeasure.hardware_preflight`, and `python -m happymeasure.diagnostics`.
- Kept the existing `keith_ivt` implementation package and imports as a compatibility layer, so old imports and fallback launch paths continue to work.
- Updated Windows launchers, PyInstaller entry points, README/docs, and namespace tests to prefer `happymeasure` while preserving `keith_ivt` fallback behavior.
