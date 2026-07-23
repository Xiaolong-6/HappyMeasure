# Release Notes — HappyMeasure 1.1b4

**Adaptive sweep editing, exact presets, and sweep reliability**

HappyMeasure 1.1b4 simplifies custom sweep entry and fixes cases where requested
setpoints or user-entered settings could be lost.

## What's new

- **Adaptive multiline editor**: Enter one `start, stop, step` segment per line.
  Positive steps scan upward and negative steps scan downward.
- **Duplicate-value option**: Repeated values can be removed globally while
  keeping the first occurrence and original scan order, or preserved when the
  measurement requires them.
- **Exact Hardware + Sweep presets**: Presets now restore every visible setting
  on the Hardware and Sweep pages without changing unrelated pages.
- **Flexible editor height**: The Adaptive text box grows with its entered line
  count and relies on the Sweep page scrollbar instead of nesting another one.

## Bug fixes

- **Complete setpoint capture**: Measurements discarded after a current-range
  change are retried at the same source value, preventing missing requested
  voltages in the saved sweep.
- **Safe numeric-field fallback**: Empty, non-numeric, and non-finite values in
  fields such as Delay, NPLC, and Compliance revert to their defaults on focus
  loss and are normalized again before a sweep starts.
- **Clean Adaptive migration**: Obsolete generated Adaptive segment rows no
  longer appear as residual text after upgrading.
- **Reliable shutdown during update checks**: Background update results are
  delivered through the UI queue, avoiding callbacks into a destroyed Tk
  interpreter when the application closes.

## Compatibility

- Existing settings and presets remain readable.
- Existing HappyMeasure CSV files remain importable.
- The public package/CLI remains `happymeasure`; `keith_ivt` remains available
  as a compatibility namespace.
- No breaking measurement-data format changes are introduced.

## Validation status

- Full automated source validation: 467 passed, 1 expected skip.
- Coverage: 95.35%, above the required 95% threshold.
- Black, Ruff, and mypy: passed.
- Desktop simulator user-flow smoke test: passed.
- Windows portable package: built with Python 3.12, required contents verified,
  and the packaged `HappyMeasure 1.1b4` window launched, responded, and closed
  normally.
- The operator confirmed successful real-device measurement and the short
  hardware release gate with the final packaged executable.

## Release artifact

- File: `HappyMeasure-1.1b4-windows-portable.zip`
- Size: 45,058,322 bytes
- SHA-256: `f19fc1ec4a2c7257c8508056df4102c59842a353d589ca0d79de1521f77318cb`

## Upgrade notes

- Review migrated presets once after upgrading if they were created before
  `1.1b4`.
- The Adaptive editor starts empty when no new-format segment text exists;
  legacy generated logarithmic rows are intentionally not restored.
- This is a beta prerelease.
