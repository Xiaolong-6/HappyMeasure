# Versioning policy

HappyMeasure uses pre-1.0 semantic versioning during the beta phase.

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
- Increment `alpha.N` or `beta.N` for internal handoff builds within the same feature phase.
- Use `.postN` only when the source behavior is unchanged, for example README typo, launcher packaging fix, or missing non-code file.

## Current baseline

`1.1b3` is the current beta release. The project is in beta phase with simulator-first validation. Real hardware validation is pending.
