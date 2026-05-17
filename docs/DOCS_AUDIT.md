# Documentation Audit

Date: 2026-05-17

## Scope

This audit checked the current `docs/` tree, top-level README, and release-prep documentation after the namespace, safety, trace/export, config-compatibility, and UI status-icon hardening passes.

## Current status

The documentation set is broad enough for alpha handoff, but the release path needed a stronger single source of truth. `docs/RELEASE_CHECKLIST.md` has therefore been expanded into the release-prep owner document covering source hygiene, version naming, documentation audit, source tests, manual smoke tests, hardware validation, version bump, portable packaging, GitHub Release, and post-release verification.

`docs/README.md` now acts as a documentation index and points developers to the document that owns each behavior area.

## Ownership map

- User overview and current status: `README.md`
- Release procedure: `docs/RELEASE_CHECKLIST.md`
- Manual simulator/UI/data checks: `docs/MANUAL_SMOKE_TESTS.md`
- CSV/import/export contract: `docs/TRACE_SCHEMA.md`
- Hardware preflight: `docs/HARDWARE_PREFLIGHT.md`
- Staged bench validation: `docs/HARDWARE_VALIDATION_PROTOCOL.md`
- Build instructions: `docs/WINDOWS_PORTABLE_BUILD.md` and `docs/WINDOWS_PYTHON314_BUILD.md`
- Machine handoff: `docs/AGENT_HANDOFF.md` and `docs/NEW_THREAD_CONTEXT.md`
- Temporary implementation diary: `docs/CODEX_DIARY_TEMP.md`

## Items intentionally not changed

- Historical references to `0.7a1` remain where they describe the current alpha release or draft release package name.
- Internal code examples using `keith_ivt` remain valid where the document is explicitly about implementation modules or legacy compatibility.
- Build execution remains deferred until after version bump/release-prep, consistent with the current workflow.

## Future cleanup candidates

These are not release blockers, but they would reduce long-term documentation debt:

1. Convert `CODEX_DIARY_TEMP.md` into polished release notes after final build validation.
2. Review older roadmap/migration docs for stale future claims such as old `0.7.0` removal targets.
3. Consider moving obsolete historical notes into an archive folder after the first externally shared beta.
4. Keep `docs/README.md` as the index; avoid adding new orphan docs without linking them there.
