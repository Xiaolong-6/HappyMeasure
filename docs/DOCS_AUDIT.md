# Documentation Audit

Last full audit: 2026-09-11, release-candidate line `1.1b6`.

## Objective

Keep the repository documentation small enough that a developer or release operator can identify the authoritative instruction without comparing several stale diaries, migration plans, implementation notes, or duplicated build recipes.

## Owners

| Subject | Owner document |
| --- | --- |
| Product/launch | `../README.md` |
| Architecture | `ARCHITECTURE_CURRENT.md` |
| State model | `STATE_MACHINE.md` |
| Error recovery | `ERROR_RECOVERY.md` |
| Operator troubleshooting / Restart UI | `TROUBLESHOOTING.md` |
| Trace/CSV contract | `TRACE_SCHEMA.md` |
| Settings compatibility | `SETTINGS_COMPATIBILITY.md` |
| Hardware validation | `HARDWARE_VALIDATION_PROTOCOL.md` |
| Map project contract | `MAP_PROJECT_FORMAT.md` |
| Release procedure | `RELEASE_CHECKLIST.md` |
| Current validation status | `VALIDATION_STATUS.md` |
| Release history | `CHANGELOG.md` and versioned release notes |
| Common Windows packaging | `WINDOWS_PORTABLE_BUILD.md` |
| Python 3.14 packaging exception | `WINDOWS_PYTHON314_BUILD.md` |

## 2026-09-11 cleanup decisions

Removed as obsolete/redundant:

- `AGENT_HANDOFF.md` — chronological implementation diary duplicated architecture/changelog/release status. Stable machine instructions live in root `AGENTS.md`; current status lives in `VALIDATION_STATUS.md`.
- `TESTED_CURRENT.md` — accumulated historical test diary. Replaced by the concise `VALIDATION_STATUS.md`; historical validation remains in Git/release notes.
- `MIGRATION_PLAN.md` — described alpha namespace phases that no longer represent the current beta policy. The stable namespace decision is owned by `NAMING.md` and `AGENTS.md`.
- `HARDWARE_DRIVER_MIGRATION.md` — 0.5→0.6 migration timeline and examples were historical and partly contradicted the current runtime. Driver-extension guidance remains in `DRIVER_SWEEP_EXTENSION_GUIDE.md` and current architecture docs.
- `SETTINGS_MIGRATION.md` — described a Pydantic/nested v2 settings migration as if it were the active desktop runtime. `1.1b6` still persists the flat `keith_ivt.data.settings.AppSettings` contract; the accurate owner is now `SETTINGS_COMPATIBILITY.md`.
- `RESTART_MECHANISM.md` — mixed current behavior with speculative launcher/marker/helper proposals. The implemented Restart UI behavior and operator caveats now live in `TROUBLESHOOTING.md`.
- `docs/screenshots/happymeasure-settings.png` — no longer referenced and represented an older Settings layout after the developer-tools/diagnostics reorganization.

Consolidated/updated:

- `ARCHITECTURE_CURRENT.md` — current component boundaries and invariants only; historical UI/theme iteration belongs in Git/release notes.
- `DRIVER_SWEEP_EXTENSION_GUIDE.md` — developer extension guidance, not a migration diary.
- `TROUBLESHOOTING.md` — owns launch/import troubleshooting, Restart UI behavior and links to the maintained build/hardware procedures.
- Windows packaging docs — `WINDOWS_PORTABLE_BUILD.md` owns the common contract; `WINDOWS_PYTHON314_BUILD.md` should contain only the Python 3.14-specific path/workaround.
- Test documentation — ownership is split into `tests/common/`, `tests/happymeasure/`, and `tests/map_reconstruction/`; obsolete source-shape regressions were replaced by stronger behavior/contract tests where needed.
- Release validation instructions — core and Map Qt gates are documented separately so optional Qt dependencies cannot create a false-green or an accidental core-install requirement.

Retained intentionally:

- Versioned release notes: immutable historical context.
- `WINDOWS_PYTHON314_BUILD.md`: still a distinct packaging exception, but not a duplicate owner for common packaging rules.
- Scientific/format contracts (`TRACE_SCHEMA.md`, `MAP_PROJECT_FORMAT.md`, `PHASE_WINDOW_RECONSTRUCTION.md`): these define reproducibility rather than implementation history.
- Hardware preflight/dry-run/validation documents: each has a different safety scope.
- `settings_v2.py` tests/code are retained as an alternate/experimental model, but current operator documentation must not present it as the active persistence format.
- Referenced UI screenshots that still illustrate current user-facing areas; stale/unreferenced screenshots are deletion candidates.

## Staleness rules

A document is a deletion/consolidation candidate when it is primarily one of:

1. a completed migration plan;
2. a chronological agent/test diary;
3. a duplicate of an owner document;
4. instructions for a version no longer supported, unless clearly retained as historical release notes;
5. a proposed architecture described as current when the runtime still uses a different owner;
6. an implementation note whose still-valid behavior can live in an existing operator/developer owner document;
7. an unreferenced screenshot or example of a UI that has materially changed.

Before deleting, search repository references and update them in the same change. Do not delete scientific format/safety contracts merely because they are old; update their current applicability instead.

## Next audit

Run another docs audit when one of these occurs:

- a release changes public file formats or hardware safety semantics;
- Map Reconstruction stops being optional;
- the `keith_ivt` compatibility namespace is intentionally removed;
- Windows packaging/updater ownership changes substantially;
- the desktop settings runtime intentionally migrates away from the flat `AppSettings` format.
