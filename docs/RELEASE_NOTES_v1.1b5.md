# Release Notes — HappyMeasure 1.1b5

**Direction-independent Step entry and recoverable sweep errors**

HappyMeasure 1.1b5 fixes descending Step sweeps that previously required a
negative step and improves validation and recovery before another measurement.

## User-facing changes

- **Step is a magnitude**: Start and Stop determine sweep direction. Positive
  and negative step entries now produce the same requested ascending or
  descending source sequence.
- **Consistent Adaptive segments**: Adaptive `start, stop, step` rows use the
  same magnitude semantics, so `20, 1, 1` and `20, 1, -1` both descend.
- **Earlier validation**: Invalid sweep parameters are reported before a worker
  starts or instrument output can be enabled. Correct the value and press Start
  again without restarting HappyMeasure.
- **Runtime recovery**: Measurement failures still show and log the underlying
  error, then return the connected UI to a usable Ready state after cleanup.

## Validation and safety hardening

- Canonical model validation rejects NaN and infinite active values for Step
  bounds, compliance, NPLC, delay, fixed ranges, range settling/discard values,
  finite Time sweeps, and manual output.
- Hysteresis continues to omit a duplicated turn point and returns to the start
  value for descending sweeps entered with a positive step magnitude.
- Existing sweep-runner and measurement-service `finally` / `output_off()`
  behavior is unchanged and remains covered by fault-injection tests.
- Runtime cleanup clears partial live points, plot buffers, worker events,
  pending range actions, and the auto-opened front-panel popup before retry.

## Compatibility

- Existing positive and negative Step/Adaptive entries remain valid.
- Settings, presets, CSV metadata, and public/legacy Python namespaces are
  unchanged.
- No measurement-data format or hardware command-sequence changes are included.

## Validation status

- Full automated source suite: 501 passed, 1 expected conditional skip;
  coverage 95.14% (required minimum 95%).
- Focused model/controller/safety suite: 63 passed.
- Ruff, compileall, and source mypy checks: passed in the available Python 3.12
  environment.
- Automated desktop simulator user-flow smoke test: passed.
- Windows portable package: built with Python 3.12; required files and ZIP
  contents verified; packaged executable remained running during the startup
  smoke check and closed cleanly afterward.
- The final `1.1b4` package passed the short real-hardware release gate. The
  `1.1b5` package still requires the short Keithley smoke test before it is
  described as hardware-verified.

## Release artifact

- File: `HappyMeasure-1.1b5-windows-portable.zip`
- Size: 44,701,070 bytes
- SHA-256: `247006dd5ba05ff421fadee7e4652ea91ab5a6cd909256f48dfc489e202431ce`

## Upgrade notes

- No migration is required.
- This is a beta prerelease.
