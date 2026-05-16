# Codex Diary (Temporary)

This temporary diary records changes made during Codex-assisted turns so release notes can be prepared later.

## 2026-05-16

### Public package namespace migration

- Promoted runtime `PACKAGE_NAME` from the legacy `keith_ivt` namespace to the public `happymeasure` namespace.
- Added `src/happymeasure` command wrappers for `python -m happymeasure`, `python -m happymeasure.hardware_preflight`, and `python -m happymeasure.diagnostics`.
- Kept the existing `keith_ivt` implementation package and imports as a compatibility layer, so old imports and fallback launch paths continue to work.
- Updated Windows launchers, PyInstaller entry points, README/docs, and namespace tests to prefer `happymeasure` while preserving `keith_ivt` fallback behavior.

### Data import/export hardening

- Hardened CSV metadata import parsing so string values such as "False" no longer become truthy booleans.
- Preserved additional sweep metadata across single and combined CSV round trips, including output-off policy, continuous-time settings, debug model, fixed ranges, and adaptive/time-sweep fields.
- Added regression tests for boolean/range metadata, constant-time sweep metadata, and long-format combined CSV import/export.
- Validation used: python -m py_compile src\keith_ivt\data\exporters.py src\keith_ivt\data\importers.py tests\test_data_import_export_store.py
- Validation used: PYTHONPATH=src python -m pytest tests\test_data_import_export_store.py tests\test_simulator_behavior.py tests\test_app_state.py -q
