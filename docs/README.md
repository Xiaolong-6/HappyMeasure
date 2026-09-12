# HappyMeasure Documentation

This index is the documentation source of truth. Prefer one owner document per contract; Git history and release notes preserve old implementation detail, so current docs should not become chronological diaries.

## Start here

- `../README.md` — product overview and launch instructions
- `../AGENTS.md` — machine/developer change discipline and safety invariants
- `../CONTRIBUTING.md` — contribution and documentation rules
- `VALIDATION_STATUS.md` — current automated/manual release status
- `TROUBLESHOOTING.md` — operator troubleshooting, including current Restart UI behavior

## Measurement and application contracts

- `ARCHITECTURE_CURRENT.md` — current component boundaries
- `STATE_MACHINE.md` — run and connection state semantics
- `ERROR_RECOVERY.md` — recoverable/fatal error behavior
- `TRACE_SCHEMA.md` — CSV/import/export metadata contract
- `SETTINGS_COMPATIBILITY.md` — active flat-settings persistence and compatibility rules
- `DRIVER_SWEEP_EXTENSION_GUIDE.md` — adding measurement/driver behavior
- `NAMING.md` — product and Python namespace rules

## Hardware and safety

- `HARDWARE_PREFLIGHT.md` — safe communication preflight
- `HARDWARE_DRY_RUN_GUIDE.md` — disconnected/dummy-load dry-run guidance
- `HARDWARE_VALIDATION_PROTOCOL.md` — staged real-hardware release gate

Hardware-facing changes must preserve validation-before-output and `output_off()` cleanup semantics. Simulator/CI success is not evidence of real-hardware verification.

## Map Reconstruction

- `MAP_PROJECT_FORMAT.md` — authoritative `.hmmap` archive contract
- `PHASE_WINDOW_RECONSTRUCTION.md` — phase-window reconstruction method
- `MAP_PACKAGING_SIZE_AUDIT.md` — standalone Windows package dependency and size audit

Map Reconstruction GUI dependencies are optional (`.[map]`). Its Windows/Python 3.12 offscreen Qt suite is a dedicated release gate.

## Release and build

- `RELEASE_CHECKLIST.md` — current release process (`1.1b6` candidate)
- `RELEASE_NOTES_v1.1b6.md` — current release-candidate notes
- `CHANGELOG.md` — concise release history
- `WINDOWS_PORTABLE_BUILD.md` — common Windows portable build contract
- `WINDOWS_PYTHON314_BUILD.md` — Python 3.14-only packaging differences/workaround
- `MANUAL_SMOKE_TESTS.md` — desktop/operator smoke checks
- `UI_VISUAL_CHECKLIST.md` — visual/responsive checks
- `UI_DIAGNOSTICS.md` — built-in UI/hardware diagnostic scope
- `UI_STYLE_GUIDE.md` — UI styling conventions
- `DOCS_AUDIT.md` — documentation ownership/cleanup record

## Historical release notes

Historical notes are intentionally retained as release records, not current instructions:

- `RELEASE_NOTES_v0.7a1.md`
- `RELEASE_NOTES_v1.0b1.md`
- `RELEASE_NOTES_v1.1b1.md`
- `RELEASE_NOTES_v1.1b3.md`
- `RELEASE_NOTES_v1.1b4.md`
- `RELEASE_NOTES_v1.1b5.md`

## Documentation policy

- Put current behavior in the owner document above.
- Put release history in `CHANGELOG.md` / release notes.
- Put current test/manual-gate status in `VALIDATION_STATUS.md`.
- Do not add date-by-date agent diaries to the repository.
- Delete migration plans after their decision has become the stable documented architecture.
- Delete superseded implementation notes after moving any still-current contract into the permanent owner document.
- Keep release-build special-case documents narrow; common packaging instructions belong in `WINDOWS_PORTABLE_BUILD.md`.
- When deleting a document, first move any still-valid contract into its permanent owner.
