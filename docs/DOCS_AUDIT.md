# Documentation Audit

Last full audit: 2026-09-11, release-candidate line `1.1b6`.

## Objective

Keep the repository documentation small enough that a developer or release operator can identify the authoritative instruction without comparing several stale diaries or migration plans.

## Owners

| Subject | Owner document |
| --- | --- |
| Product/launch | `../README.md` |
| Architecture | `ARCHITECTURE_CURRENT.md` |
| State model | `STATE_MACHINE.md` |
| Error recovery | `ERROR_RECOVERY.md` |
| Trace/CSV contract | `TRACE_SCHEMA.md` |
| Settings compatibility | `SETTINGS_MIGRATION.md` |
| Hardware validation | `HARDWARE_VALIDATION_PROTOCOL.md` |
| Map project contract | `MAP_PROJECT_FORMAT.md` |
| Release procedure | `RELEASE_CHECKLIST.md` |
| Current validation status | `VALIDATION_STATUS.md` |
| Release history | `CHANGELOG.md` and versioned release notes |

## 2026-09-11 cleanup decisions

Removed as obsolete/redundant:

- `AGENT_HANDOFF.md` — chronological implementation diary duplicated architecture/changelog/release status. Stable machine instructions live in root `AGENTS.md`; current status lives in `VALIDATION_STATUS.md`.
- `TESTED_CURRENT.md` — accumulated historical test diary. Replaced by the concise `VALIDATION_STATUS.md`; historical validation remains in Git/release notes.
- `MIGRATION_PLAN.md` — described alpha namespace phases that no longer represent the current beta policy. The stable namespace decision is owned by `NAMING.md` and `AGENTS.md`.
- `HARDWARE_DRIVER_MIGRATION.md` — 0.5→0.6 migration timeline and examples were historical and partly contradicted the current runtime. Driver-extension guidance remains in `DRIVER_SWEEP_EXTENSION_GUIDE.md` and current architecture docs.

Retained intentionally:

- Versioned release notes: immutable historical context.
- `WINDOWS_PYTHON314_BUILD.md`: still a distinct packaging path.
- Scientific/format contracts (`TRACE_SCHEMA.md`, `MAP_PROJECT_FORMAT.md`, `PHASE_WINDOW_RECONSTRUCTION.md`): these define reproducibility rather than implementation history.
- Hardware preflight/dry-run/validation documents: each has a different safety scope.

## Staleness rules

A document is a deletion/consolidation candidate when it is primarily one of:

1. a completed migration plan;
2. a chronological agent/test diary;
3. a duplicate of an owner document;
4. instructions for a version no longer supported, unless clearly retained as historical release notes.

Before deleting, search repository references and update them in the same change. Do not delete scientific format/safety contracts merely because they are old; update their current applicability instead.

## Next audit

Run another docs audit when one of these occurs:

- a release changes public file formats or hardware safety semantics;
- Map Reconstruction stops being optional;
- the `keith_ivt` compatibility namespace is intentionally removed;
- Windows packaging/updater ownership changes substantially.
