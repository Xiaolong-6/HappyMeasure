# Versioning policy

HappyMeasure uses pre-1.0 semantic versioning during the offline alpha migration.

## Format

```text
MAJOR.MINOR.PATCH[-alpha.N|-beta.N|-rc.N][.postN]
```

## Meaning

- `0.x.y`: pre-1.0 development. APIs, UI layout, and hardware abstractions may still change.
- `alpha.N`: internal handoff/testing build. Simulator-first validation is required before handoff.
- `beta.N`: feature-complete enough for broader testing. UI/data formats should be mostly stable.
- `rc.N`: release candidate. Only blocker fixes should be accepted.
- `.postN`: packaging/documentation-only correction after a tagged build. Do not use `.postN` for feature work or behavior changes.

## When to increment

- Increment `MINOR` for visible UI workflow changes, new measurement modes, data-model changes, or meaningful architecture splits.
- Increment `PATCH` for bug fixes that preserve the current feature scope.
- Increment `alpha.N` for internal handoff builds within the same feature phase.
- Use `.postN` only when the source behavior is unchanged, for example README typo, launcher packaging fix, or missing non-code file.

## Current baseline

`0.3.0-alpha.1` is the cleaned baseline for the former `0.2.5.post6` feature state. It includes drawer navigation, bottom status bar connection light, live-only plotting during active measurements, trace-list data actions, constant-until-stop time sweeps, and the first UI module splits.

## Planned lines

- `0.3.x-alpha.N`: UI/simulator stabilization and continued `simple_app.py` split.
- `0.4.x-alpha.N`: real hardware integration hardening for Keithley 2400/2450 paths.
- `1.0.0`: only after real hardware safety, abort/output-off behavior, data export format, launcher, and UI workflow are stable.
