# Current Validation Status

This file records the validation scope that applies to the current development HEAD. The authoritative automated result is the GitHub Actions status for that exact commit; do not copy old run IDs forward as though they validate newer source.

## Current release-prep decision

The development line is in **release audit**. Publication requires all source/Qt/version/privacy jobs plus the Windows portable package job to be green on the final selected commit. README screenshots must also reflect the final visible UI before publication.

## Automated source gate

Required for release:

- Windows Python 3.11/3.12/3.13/3.14: compileall, Black, Ruff, mypy and core pytest;
- Python 3.14 configured core coverage `>=95%`;
- dedicated Windows/Python 3.12 Map Reconstruction job with real PySide6/pyqtgraph dependencies and offscreen Qt tests;
- per-commit internal version sequence check;
- repository privacy regression preventing workstation-specific home paths and known real instrument serial identifiers from returning;
- version/namespace/settings/export/safety regressions.

A green source gate validates source behavior only. Package readiness additionally requires the package job below.

## Real-hardware evidence retained for this release line

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

No passive-load resistor test was performed in this release-prep session. Therefore the repository must **not** claim quantitative source/readback accuracy, calibrated resistance accuracy, arbitrary DUT validation, or physical validation of every supported 2400-family model. Additional hardware testing is optional for this release unless later code changes materially alter hardware I/O/safety behavior.

## Automated Windows package gate

On pushes to `main`, `Windows portable package smoke (Python 3.12)` runs after the source and Map gates. For the exact commit it:

1. clean-builds both portable applications;
2. audits package structure and release contents;
3. rejects tracked/private workstation identifiers in packaged text;
4. rejects runtime logs/test/build/hardware-smoke debris;
5. enforces Map Reconstruction ZIP/extracted size ceilings;
6. smoke-launches both frozen executables; and
7. emits audited ZIPs plus `release-artifacts.json` containing SHA-256 and size data.

A package job from an older commit is not evidence for a newer commit.

## Screenshot/documentation gate

The six README screenshots under `docs/screenshots/` are part of the release documentation surface. When visible UI has changed, refresh them from the final Windows candidate before publication. Captures must not expose usernames, workstation paths, instrument serial numbers or unrelated desktop content.

## Status vocabulary

- **SOURCE READY** — automated source/Qt/version/privacy gates pass on the exact commit.
- **PACKAGE READY** — source gate plus the Windows portable package build/audit/smoke job passes on the exact commit.
- **2401 NO-DUT VERIFIED** — the recorded communication/control/safety smoke above passed; this is deliberately narrower than analog/DUT validation.
- **RELEASE CANDIDATE READY** — SOURCE READY + PACKAGE READY + current release screenshots/documentation.
- **RELEASED** — a human selected the public version, tag/release/artifacts were published, and post-release download/update checks passed.
