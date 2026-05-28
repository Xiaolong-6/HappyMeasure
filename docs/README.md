# HappyMeasure Documentation Index

This directory contains both user-facing release documents and machine-facing handoff notes. Start here before editing docs so release-critical information stays in one place rather than being scattered across README fragments.

## Human-facing quick path

Use these first:

- `../README.md` — human project overview and current user status.
- `CHANGELOG.md` — release history.
- `RELEASE_CHECKLIST.md` — source validation, version bump, packaging, GitHub Release, and post-release verification.
- `MANUAL_SMOKE_TESTS.md` — manual UI/simulator/data smoke checks.
- `TROUBLESHOOTING.md` — common runtime and hardware issues.

## Hardware and safety path

Use in this order before real DUT measurement:

- `HARDWARE_PREFLIGHT.md` — safe CLI preflight behavior and expected PASS/FAIL output.
- `HARDWARE_DRY_RUN_GUIDE.md` — simulator and no-DUT checks.
- `HARDWARE_VALIDATION_PROTOCOL.md` — staged bench validation from cable-only to real DUT (includes safety rules).
- `ERROR_RECOVERY.md` — recovery expectations after errors.

## Build and release packaging

- `WINDOWS_PORTABLE_BUILD.md` — standard Windows portable-folder build.
- `WINDOWS_PYTHON314_BUILD.md` — Python 3.14-specific build notes and caveats.
- `RELEASE_CHECKLIST.md` — final release-prep sequence; build validation is intentionally a late step after version updates.
- `RELEASE_NOTES_v1.1b3.md` — current release notes.

## Architecture and developer references

- `ARCHITECTURE_CURRENT.md` — current architecture map and design decisions.
- `MIGRATION_PLAN.md` — staged `keith_ivt` -> `happymeasure` namespace migration plan.
- `STATE_MACHINE.md` — run/connection state contracts.
- `TRACE_SCHEMA.md` — CSV v2 trace metadata/import/export contract.
- `SETTINGS_MIGRATION.md` — settings-schema migration notes.
- `DRIVER_SWEEP_EXTENSION_GUIDE.md` — adding drivers and sweep paths.
- `HARDWARE_DRIVER_MIGRATION.md` — driver-layer migration notes.
- `RESTART_MECHANISM.md` — UI restart behavior.
- `UI_STYLE_GUIDE.md` and `UI_VISUAL_CHECKLIST.md` — UI styling and visual checks.
- `NAMING.md` — naming conventions.
- `VERSIONING.md` — versioning policy.

## Agent handoff notes

- `AGENT_HANDOFF.md` — detailed machine-facing current context.
- `DOCS_AUDIT.md` — latest documentation ownership audit and cleanup candidates.

## Test documentation

- `../tests/README.md` — test map and validation gates.
- `TESTED_CURRENT.md` — current test results snapshot.

## Historical release notes

- `RELEASE_NOTES_v0.7a1.md` — v0.7a1 release notes.
- `RELEASE_NOTES_v1.0b1.md` — v1.0b1 release notes.
- `RELEASE_NOTES_v1.1b1.md` — v1.1b1 release notes.

## Namespace convention

Use `happymeasure` for public launch commands and documentation. The legacy `keith_ivt` namespace remains available for existing imports while the implementation is migrated incrementally.

## Documentation maintenance rule

When behavior changes, update the most specific document that owns the behavior:

- UI/manual behavior: `README.md` and/or `MANUAL_SMOKE_TESTS.md`.
- CSV/import/export behavior: `TRACE_SCHEMA.md`.
- Hardware safety/preflight: `HARDWARE_PREFLIGHT.md` and `HARDWARE_VALIDATION_PROTOCOL.md`.
- Packaging/release process: `RELEASE_CHECKLIST.md` and build docs.
- Machine handoff context: `AGENT_HANDOFF.md`.

Avoid duplicating long procedures in multiple files. Link to the owner document instead.
