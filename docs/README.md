# HappyMeasure Documentation

This index is the documentation source of truth. Current behavior belongs in an owner document; obsolete migration diaries and stale version-specific instructions should be removed rather than preserved as active documentation.

## Start here

- `../README.md` — product overview, launch instructions, project-hub links and release screenshots
- `../AGENTS.md` — machine/developer change discipline and safety invariants
- `../CONTRIBUTING.md` — contribution, versioning and validation rules
- `VALIDATION_STATUS.md` — current validation scope and release readiness definitions
- `TROUBLESHOOTING.md` — operator troubleshooting

## Measurement and application contracts

- `ARCHITECTURE_CURRENT.md` — current component boundaries
- `STATE_MACHINE.md` — run and connection state semantics
- `ERROR_RECOVERY.md` — recoverable/fatal error behavior
- `TRACE_SCHEMA.md` — CSV/import/export metadata contract
- `SETTINGS_COMPATIBILITY.md` — flat-settings persistence and compatibility rules
- `DRIVER_SWEEP_EXTENSION_GUIDE.md` — measurement/driver extension guidance
- `NAMING.md` — product and Python namespace rules

## Hardware and safety

- `HARDWARE_PREFLIGHT.md` — safe serial preflight and COM/baud behavior
- `HARDWARE_DRY_RUN_GUIDE.md` — disconnected/no-DUT dry-run guidance
- `HARDWARE_VALIDATION_PROTOCOL.md` — staged real-hardware validation and evidence scope

Simulator/CI success is not proof of real-hardware compatibility. Existing MODEL 2401 no-DUT evidence is recorded in `VALIDATION_STATUS.md` without publishing the instrument serial number.

## Release and build

- `VERSIONING.md` — internal per-commit build numbering and human release-version policy
- `RELEASE_CHECKLIST.md` — release procedure, automated package gate and screenshot refresh gate
- `RELEASE_NOTES_NEXT.md` — next public release draft
- `CHANGELOG.md` — concise historical release record
- `WINDOWS_PORTABLE_BUILD.md` — Windows portable build/audit contract
- `WINDOWS_PYTHON314_BUILD.md` — Python 3.14 packaging exception
- `MANUAL_SMOKE_TESTS.md` — optional desktop/operator smoke checks
- `UI_VISUAL_CHECKLIST.md` — visual/responsive checks
- `UI_DIAGNOSTICS.md` — built-in diagnostics scope
- `UI_STYLE_GUIDE.md` — UI styling conventions

The automated `main` package job builds the HappyMeasure portable ZIP, audits package contents/privacy, smoke-launches the frozen executable, generates SHA-256 metadata, and uploads the audited candidate for the exact commit.

## Browser analysis tools

The HappyMeasure Pages hub links to the independently maintained **HM-Map-Reconstruction** and **HM-IV-Fitter** repositories. Their implementation documentation and deployment status belong in those repositories, not here.

## Release screenshots

The three PNG files under `screenshots/` referenced by the root README are the active HappyMeasure desktop release screenshots. Refresh stale captures from the exact final source candidate whenever visible desktop UI changes before a future release.

Historical desktop Map Reconstruction documentation and screenshots remain available in Git history and published release records, but are not part of the current source tree.

## Documentation policy

- Keep one current owner document per contract.
- Delete superseded implementation notes after preserving any still-valid contract in its owner document.
- Do not add chronological agent/test diaries.
- Do not commit workstation usernames, home-directory paths, private local paths, or physical instrument serial numbers.
- Release notes must use portable relative paths and sanitized hardware identifiers.
- Do not publish a release with README screenshots that visibly contradict the final packaged UI.
