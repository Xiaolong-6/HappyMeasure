# Release Checklist — HappyMeasure

Use this checklist from a clean release candidate after feature freeze. The public release version is selected by a human only after the internal build passes the release audit.

## 1. Identity and tree hygiene

Before tagging:

```powershell
git status --short
git log --oneline -8
```

Confirm:

- `src/keith_ivt/version.py` and `pyproject.toml` report the same internal build;
- every commit since the previous parent increments the internal beta serial by one;
- no generated/runtime folders, local helper scripts, logs, hardware-smoke artifacts, `build/` or `dist/` are committed;
- no workstation-specific absolute home paths, usernames or physical instrument serial numbers are present in tracked text;
- `docs/RELEASE_NOTES_NEXT.md` describes the release draft without pretending the internal build number is already the public version.

## 2. Automated core validation

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
```

Coverage gate remains `>=95%` for the configured core scope.

## 3. Map Reconstruction release gate

```powershell
python -m pip install -e ".[dev,map]"
$env:QT_QPA_PLATFORM="offscreen"
python -c "import PySide6, pyqtgraph"
python -m mypy src/map_reconstruction
python -m pytest -q tests/map_reconstruction
```

CI owns a dedicated Windows/Python 3.12 job with real Qt dependencies. Dependency-driven skips do not count as a release-gate pass.

For the complete local release environment:

```powershell
python tests\run_full_validation.py
```

## 4. Desktop simulator/UX smoke

Follow `MANUAL_SMOKE_TESTS.md` and `UI_VISUAL_CHECKLIST.md`. Pay particular attention to:

- repeated Start/Pause/Resume/Stop/restart;
- live Time plot switching between All data and Last N while running;
- Settings review/save, including Auto-save backup and Record log;
- Developer Tools visibility and repeatable UI/Hardware Diagnostics buttons;
- trace import/export/rename/delete;
- Map CSV replacement, project round-trip and normal/maximized window behavior.

## 5. Hardware evidence

The current release line already has MODEL 2401 no-DUT communication/control evidence recorded in `VALIDATION_STATUS.md`. Do not require another bench session unless later source changes touch serial I/O, source-output safety, acquisition sequencing or hardware cleanup.

If such behavior changes, rerun the relevant portion of `HARDWARE_VALIDATION_PROTOCOL.md` before release.

Do not upgrade the claim beyond the recorded evidence: no passive-load quantitative accuracy or arbitrary DUT validation was performed in the current release-prep session.

## 6. Windows portable packages

Build only after source gates pass. Build scripts use dedicated build environments and must not depend on a developer workstation path.

HappyMeasure:

```powershell
.\tools\build\Build_Portable_Windows_App.ps1
```

Map Reconstruction:

```powershell
.\tools\build\Build_Portable_Map_Reconstruction.ps1
```

Verify both packages launch without system Python and do not contain local logs, caches, source checkout paths or hardware-smoke artifacts. Record artifact size and SHA-256.

## 7. Human release-version decision

After all gates are green, a human chooses the public version/tag. Make runtime/package/artifact/tag identity consistent before publication. Never reuse an already published version for different source.

Create the public release from the exact verified commit and upload only the freshly rebuilt artifacts.

## 8. Post-release

- download each uploaded artifact to a fresh folder and launch it;
- verify hashes and version identity;
- test update detection from the previous public release;
- verify offline update-check failure is non-blocking;
- keep final release evidence in the GitHub Release/changelog, not a workstation-specific path in source documentation.
