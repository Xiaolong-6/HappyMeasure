# Namespace Migration Plan

HappyMeasure is moving from the historical implementation namespace `keith_ivt` to the public namespace `happymeasure`.

## Current decision

For the current alpha line, `happymeasure` is the public launch and documentation namespace, while `keith_ivt` remains the internal implementation namespace and compatibility layer.

This is intentional. A full source-tree rename before hardware validation would create unnecessary risk in imports, PyInstaller entry points, tests, and existing user scripts.

## Current state

| Area | Public namespace | Implementation / compatibility status |
| --- | --- | --- |
| App launch | `python -m happymeasure` | Delegates to the existing UI implementation. |
| Legacy launch | `python -m keith_ivt` | Retained for compatibility. |
| Hardware preflight | `python -m happymeasure.hardware_preflight` | Public wrapper around the implementation preflight. |
| Diagnostics | `python -m happymeasure.diagnostics` | Public wrapper around legacy diagnostics. |
| Core implementation | Not yet fully migrated | Still primarily under `src/keith_ivt/`. |
| Tests | Mixed | Test public entry points through `happymeasure` and implementation contracts through `keith_ivt`. |

## Phase 1: v0.7.x alpha compatibility layer

Status: active.

Goals:

- Keep `happymeasure` as the product/package namespace exposed in README, launchers, scripts, and release notes.
- Keep `keith_ivt` imports working for existing scripts and internal modules.
- Avoid broad import churn before real hardware validation.
- Document every public command using `happymeasure` first and `keith_ivt` only as legacy compatibility.

Do not:

- Move large implementation modules only for naming aesthetics.
- Remove `keith_ivt` imports while tests, build scripts, or launchers still need them.
- Break `Run_HappyMeasure.bat` or existing `python -m keith_ivt` compatibility.

## Phase 2: v0.8-v0.9 incremental implementation migration

Candidate order:

1. Pure data/model modules with low hardware risk.
2. Import/export and settings modules after schema stability is confirmed.
3. Diagnostics and preflight wrappers after real hardware smoke tests.
4. UI modules only after the AppState and controller boundaries are stable.

Rules:

- Migrate one module family at a time.
- Keep compatibility shims in `keith_ivt` while tests and user scripts are updated.
- Add regression tests for both public and legacy import paths during each move.
- Update `docs/README.md`, `docs/AGENT_HANDOFF.md`, and this plan after each migration step.

## Phase 3: v1.0 compatibility decision

Before v1.0, decide whether `keith_ivt` should be:

1. Removed entirely.
2. Kept as a thin deprecated compatibility shim.
3. Kept indefinitely for laboratory scripts that already import it.

The decision should be based on real usage, build stability, and hardware validation results rather than naming preference alone.

## Release rules

- Public commands in user-facing docs should prefer `happymeasure`.
- Internal architecture docs may mention `keith_ivt` when describing current implementation modules.
- Release notes must mention any namespace behavior change.
- Build validation must check both public and legacy module entry points until compatibility is intentionally removed.

## Deferred policy items

The external audit also flagged strict mypy settings and coverage thresholds. Those are engineering-policy decisions, not namespace blockers. Keep them deferred until after the next alpha release unless they block CI or release validation.
