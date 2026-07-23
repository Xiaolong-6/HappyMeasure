# Release Notes — HappyMeasure 1.1b3

**Keithley front-panel current range control**

HappyMeasure 1.1b3 adds front-panel current-range control for Keithley 2400/2401-style instruments, along with stability fixes for CSV metadata round-trips and sweep validation.

## What's new

- **Front-panel current-range popup**: Expanded the Keithley-style front-panel with current autorange state, actual current range, fixed-range selection, `Lock current range`, last range-change age, settle delay, and discard-count controls.
- **Current-range SCPI accessors**: Added SCPI command support for reading and setting current range on Keithley 2400/2401 style drivers.
- **Sweep-runner range-change settling**: Readings immediately after manual or automatic current-range changes are settled/discarded before they enter live traces, saved results, or CSV export.
- **Deterministic simulator support**: The debug simulator now supports autorange actual-range changes for consistent testing.

## Bug fixes

- **NPLC validation for constant-time sweeps**: Fixed the interval validation so it no longer includes serial overhead, allowing shorter intervals for constant-time sweeps.
- **CSV import/export metadata round-trip**: Fixed device_name, operator, mode, and autorange being lost during CSV save/load cycles.
- **Plot I-V orientation for current-source mode**: The Linear view now correctly shows Current (A) on the x-axis and Voltage (V) on the y-axis for current-source sweeps.
- **Complete setpoint capture across autorange changes**: Discarded transient readings are now repeated at the same source voltage instead of advancing to the next voltage and leaving gaps in the result.

## Validation

- 406 tests pass (1 skipped)
- Coverage: 95.06% (meets the 95% threshold)
- Version consistency verified across pyproject.toml, version.py, README.md, and CHANGELOG.md
- No simulator-level regressions found; hardware validation pending

## Upgrade notes

- Users upgrading from 1.1b2 will see the new front-panel current-range controls when using the Hardware popup.
- Existing CSV files remain compatible. The metadata round-trip fix only affects newly saved files.
- No breaking changes from 1.1b2.
