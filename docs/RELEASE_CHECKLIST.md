# Release Checklist — HappyMeasure

Use this checklist from a clean release candidate after feature freeze. Select the public release identity explicitly before the final screenshot/package pass; do not infer it from an arbitrary development build number.

## 1. Identity and tree hygiene

Before tagging:

```powershell
git status --short
git log --oneline -8
```

Confirm:

- `src/keith_ivt/version.py` and `pyproject.toml` resolve to the same identity;
- if `tools/release/RELEASE_FREEZE_MARKER` exists, all three resolve to the explicitly selected public release identity;
- while a freeze marker exists, screenshot/documentation/packaging/release-only commits preserve that frozen identity instead of incrementing the beta serial;
- no generated/runtime folders, local helper scripts, logs, hardware-smoke artifacts, `build/` or `dist/` are committed;
- no workstation-specific absolute home paths, usernames or physical instrument serial numbers are present in tracked text;
- `docs/RELEASE_NOTES_NEXT.md` describes the selected release scope accurately.

## 2. Automated source validation

Install developer dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Run:

```powershell
python tools\release\check_version_sequence.py --base HEAD^ --head HEAD
python -m compileall -q src tests tools\release
python -m black --check src tests tools\release
python -m ruff check src tests tools\release
python -m mypy src/keith_ivt src/happymeasure
python -m pytest -q tests/common tests/happymeasure
python -m pytest tests/common tests/happymeasure --cov=keith_ivt --cov-report=term -q
python tests\run_full_validation.py
```

Coverage gate remains `>=95%` for the configured core scope.

## 3. Desktop simulator/UX and screenshots

Automated HappyMeasure UI regressions own state-flow, settings/diagnostics rebuild, live Time-history switching, trace/export behavior and simulator paths.

Before public release, refresh the README screenshots under `docs/screenshots/` from the exact final source candidate and visually inspect them:

- `happymeasure-hardware.png`
- `happymeasure-sweep-result.png`
- `happymeasure-front-panel-popup.png`

A screenshot refresh is documentation maintenance, not hardware validation. Do not include usernames, private paths, physical serial numbers or unrelated desktop content in captures.

## 4. Hardware evidence

Existing release-line hardware evidence is recorded in `VALIDATION_STATUS.md`. Do not require another bench session unless later source changes touch serial I/O, source-output safety, acquisition sequencing or hardware cleanup.

If such behavior changes, rerun only the relevant portion of `HARDWARE_VALIDATION_PROTOCOL.md` before release.

Do not upgrade the claim beyond the recorded evidence: no passive-load quantitative accuracy or arbitrary DUT validation was performed in the retained MODEL 2401 session.

## 5. Windows portable package CI

The `Windows portable package smoke (Python 3.12)` job runs on every push to `main` after the source gates pass. It must be green on the exact commit selected for release. The job:

1. builds the HappyMeasure portable application from that commit;
2. audits package structure, forbidden local/runtime content and private identifiers;
3. smoke-launches the frozen executable without relying on the source entry point;
4. generates `release-artifacts.json` with artifact size and SHA-256; and
5. uploads the versioned ZIP plus manifest as a short-lived CI artifact.

The local equivalent is:

```powershell
.\tools\build\Build_Portable_Windows_App.ps1
python tools\release\audit_portable_artifacts.py --dist dist --manifest dist\release-artifacts.json
```

Never publish an older locally cached ZIP when a newer commit has been selected. Use artifacts built from the exact final commit.

## 6. Release publication

After all automated gates are green and screenshots are current, tag and publish the exact selected commit with runtime/package/artifact/tag identity kept consistent. Never reuse an already published version for different source and never replace an existing release asset with a different binary while pretending it is the same build.

If a release freeze is active, keep the marker until publication and post-download verification are complete.

## 7. Post-release

- download each uploaded artifact to a fresh folder and verify filename, byte size, SHA-256 and version identity;
- test update detection from the previous public release;
- verify offline update-check failure is non-blocking;
- keep final release evidence in the GitHub Release/changelog, not a workstation-specific path in source documentation;
- after publication, remove the release-freeze marker and resume normal numbered beta development in a dedicated transition commit; use `[release-version]` for that one transition when the frozen public identity is not a numbered beta serial.
