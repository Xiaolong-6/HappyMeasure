# Current Validation Status

This file records validation scope for the current development HEAD. The authoritative automated result is the GitHub Actions status for the exact commit; published-release evidence must not be copied forward as though it automatically validates newer source.

## Current development decision

HappyMeasure **v1.2b** was published and independently verified from commit `111337bb1aeb1927ab97922c616f767daf005a6e` on 2026-09-15. Development has resumed at **1.2b1** with no active release freeze. This post-release transition changes version/release-process metadata only and does not alter measurement or hardware behavior.

## Automated source gate

Required on current development commits and again for any future release candidate:

- Windows Python 3.11/3.12/3.13/3.14: compileall, Black, Ruff, mypy and core pytest;
- Python 3.14 configured core coverage `>=95%`;
- dedicated Windows/Python 3.12 Map Reconstruction job with real PySide6/pyqtgraph dependencies and offscreen Qt tests;
- commit-by-commit version-policy check;
- repository privacy regression preventing workstation-specific home paths and known real instrument serial identifiers from returning;
- version/namespace/settings/export/safety regressions.

A green source gate validates source behavior only. Package readiness additionally requires the package job below.

## Real-hardware evidence retained from the v1.2b baseline

A real **Keithley MODEL 2401** no-DUT session on Windows passed the release smoke path with the instrument configured at the operator-selected serial settings. The physical serial number is intentionally not stored in the repository.

Verified scope included:

- explicit serial preflight;
- `OUTPUT OFF` command and `:OUTP? -> 0` verification;
- valid MODEL 2401 `*IDN?` response;
- no-DUT 0 V runs;
- Standard acquisition;
- Fast fixed-range acquisition;
- Fast Auto-range acquisition;
- pause/resume without catch-up behavior;
- Stop followed by immediate restart;
- SCPI ordering / no unintended hot-path range polling;
- output-off cleanup after the exercised cases.

No passive-load resistor test was performed in that session. Therefore the repository must **not** claim quantitative source/readback accuracy, calibrated resistance accuracy, arbitrary DUT validation, or physical validation of every supported 2400-family model. This evidence may be retained across later commits only while hardware I/O, source-output safety, acquisition sequencing and cleanup behavior remain materially unchanged.

## Automated Windows package gate

On pushes to `main`, `Windows portable package smoke (Python 3.12)` runs after the source and Map gates. For the exact commit it:

1. clean-builds both portable applications;
2. audits package structure and release contents;
3. rejects tracked/private workstation identifiers in packaged text;
4. rejects runtime logs/test/build/hardware-smoke debris;
5. enforces Map Reconstruction ZIP/extracted size ceilings;
6. smoke-launches both frozen executables; and
7. emits audited ZIPs plus `release-artifacts.json` containing SHA-256 and size data.

A package job from an older commit is not evidence for a newer commit. Release artifacts must come from the exact commit that is tagged and published.

## Screenshot/documentation gate

The six README screenshots under `docs/screenshots/` document the published v1.2b UI. If visible UI changes before a future release, refresh the affected captures from the exact final source candidate and review them before publication. Captures must not expose usernames, workstation paths, instrument serial numbers or unrelated desktop content.

## Status vocabulary

- **SOURCE READY** — automated source/Qt/version/privacy gates pass on the exact commit.
- **PACKAGE READY** — source gate plus the Windows portable package build/audit/smoke job passes on the exact commit.
- **2401 NO-DUT VERIFIED** — the recorded communication/control/safety smoke above passed; this is deliberately narrower than analog/DUT validation.
- **RELEASE CANDIDATE READY** — SOURCE READY + PACKAGE READY + approved current release screenshots/documentation.
- **RELEASED** — the selected commit/tag/release/artifacts were published and post-release download/update checks passed.

Published `v1.2b` satisfies **RELEASED**, including independent post-download filename, byte-size and SHA-256 verification of both portable ZIPs.
