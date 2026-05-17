# Release Checklist

This checklist is the release-prep source of truth. Run it from a clean working tree after feature work is frozen and before publishing a GitHub Release.

## 0. Release identity

Set these values before starting the checklist:

- Release version: `0.7a1` or the next PEP 440 version.
- Git tag: `v0.7a1` or the matching `vX.Y...` tag.
- Portable zip name: `HappyMeasure-<version>-windows-portable.zip`.
- Release channel: `alpha`, `beta`, or `stable`.
- Target Python for source validation: project default from `pyproject.toml`.
- Target Python for Windows portable build: the build script selected interpreter; Python 3.12 is preferred when available, Python 3.14 remains experimental.

## 1. Source tree hygiene

Run from the repository root:

```powershell
git status --short
git diff --stat
```

Confirm:

- No generated/runtime folders are staged: `__pycache__`, `.pytest_cache`, `.coverage`, `htmlcov`, `build`, `dist`, `logs`, `backups`, `.pycache_tmp`, `.tmp-build`, `.build-deps`, `.pip-cache`.
- No local helper scripts are staged, especially `LOCAL_*.bat` or `LOCAL_*.ps1`.
- `LICENSE`, `NOTICE.md`, `README.md`, `CONTRIBUTING.md`, and this checklist are present.
- `.gitignore` still excludes local runtime/build helpers.
- README hardware warnings and manual-update wording are current.
- Every behavior/build/UI/safety change has one of: user-facing README note, docs update, changelog/release-note entry, or an explicit no-docs-needed rationale in the diary.

## 2. Version and naming consistency

Confirm all version-bearing files agree:

- `src/keith_ivt/version.py`
- `pyproject.toml`
- `README.md`
- `docs/CHANGELOG.md`
- `docs/RELEASE_NOTES_<version>.md` if a per-release note exists
- Any validation/build scripts that embed the release name or zip name

Confirm namespace wording:

- Public product/package namespace is `HappyMeasure` / `happymeasure`.
- Legacy implementation/compatibility namespace is `keith_ivt`.
- New public launch examples prefer `python -m happymeasure`.
- Legacy examples using `keith_ivt` are clearly marked as compatibility paths.

Recommended checks:

```powershell
python -m pytest tests\test_version_consistency.py tests\test_namespace_migration.py -q
python -m pytest tests\test_launcher_space_safe.py -q
```

## 3. Documentation audit

Review the docs index first:

```text
docs\README.md
```

Then confirm the release-relevant docs are current:

- `docs/CHANGELOG.md` — human release history.
- `docs/RELEASE_CHECKLIST.md` — this file.
- `docs/MANUAL_SMOKE_TESTS.md` — manual UI/data smoke procedure.
- `docs/TRACE_SCHEMA.md` — CSV/import/export metadata contract.
- `docs/HARDWARE_PREFLIGHT.md` — safe preflight behavior.
- `docs/HARDWARE_VALIDATION_PROTOCOL.md` — staged bench validation.
- `docs/WINDOWS_PORTABLE_BUILD.md` and `docs/WINDOWS_PYTHON314_BUILD.md` — packaging notes.
- `docs/AGENT_HANDOFF.md` and `docs/NEW_THREAD_CONTEXT.md` — machine-facing continuation notes.

Do not publish temporary/local-only runtime artifacts. `docs/CODEX_DIARY_TEMP.md` may stay in source control during alpha handoff, but release notes should be prepared from it rather than copied verbatim to end users.

## 4. Source validation

Install developer dependencies:

```powershell
python -m pip install -r requirements-dev.txt
```

Run the full validation script when available:

```powershell
python tests\run_full_validation.py
```

If Python 3.14 reports pycache or temp-file permission errors on Windows, rerun with a temporary cache prefix:

```powershell
$env:PYTHONPYCACHEPREFIX = Join-Path (Get-Location) ".pycache_tmp"
python tests\run_full_validation.py
```

Run focused release-hardening tests:

```powershell
python -m pytest tests\test_engineering_baseline.py tests\test_update_check.py -q
python -m pytest tests\test_config_compatibility.py tests\test_trace_schema_contract.py tests\test_hardware_preflight_cli.py -q
python -m pytest tests\test_fault_injection_safety.py tests\test_sweep_safety.py tests\test_app_state.py -q
python -m pytest tests\test_data_import_export_store.py tests\test_trace_selection_export_consistency.py -q
python -m pytest tests\test_start_config_regression.py tests\test_status_light_emoji_font.py -q
```

Optional desktop-only Tk smoke test:

```powershell
$env:HAPPYMEASURE_RUN_TK_SMOKE="1"
python -m pytest tests\test_ui_smoke.py -q
Remove-Item Env:\HAPPYMEASURE_RUN_TK_SMOKE
```

## 5. Manual simulator smoke checks

Follow `docs/MANUAL_SMOKE_TESTS.md`. At minimum, confirm:

- `Run_HappyMeasure.bat` starts the app from the repository root.
- Debug simulator connect/disconnect works.
- Start works from `idle`, then again after `completed`, `stopped`, and `aborted` ready states.
- Pause/Stop/Abort do not leave the status bar stuck in `Sweeping`.
- Canvas connection/simulator status icons remain fixed-size when UI font size changes.
- Trace rename/hide/delete/export/import behavior matches `docs/TRACE_SCHEMA.md`.
- Update reminder remains non-intrusive and does not download, install, or replace files.

Record any deviation in `docs/CODEX_DIARY_TEMP.md` before release notes are finalized.

## 6. Hardware validation gate

Do not run a real DUT sweep until staged validation passes.

First run CLI help with no hardware attached:

```powershell
python -m happymeasure.hardware_preflight --help
python -m keith_ivt.hardware_preflight --help
```

Then follow `docs/HARDWARE_VALIDATION_PROTOCOL.md` in order:

- Level 0: communication cable only, no DUT.
- Level 1: dummy resistors.
- Level 2: diode or robust test device.
- Level 3: real DUT.

For each hardware step, record:

- instrument model and firmware from `*IDN?`
- serial/VISA resource and terminal path
- wiring/dummy-load details
- compliance settings
- whether `output_off` was confirmed after Stop/Abort/error
- generated CSV files and runtime logs

Preflight must remain safe: open serial, query `*IDN?`, send output off, close resource. It must not source voltage/current or run a sweep.

## 7. Version bump and release notes

After source/manual validation passes:

- Update `src/keith_ivt/version.py`.
- Update `pyproject.toml` version and description if needed.
- Update README current version and "What changed" bullets.
- Update `docs/CHANGELOG.md`.
- Prepare or update `docs/RELEASE_NOTES_<version>.md`.
- Ensure release notes distinguish user-facing changes from developer/internal hardening.
- Confirm update-check behavior still compares the local version against GitHub release tags correctly.

Rerun the version/namespace checks from section 2 after changing versions.

## 8. Windows portable packaging

Build the portable Windows folder app only after sections 1-7 pass:

```powershell
.\tools\build\Build_Portable_Windows_App.ps1
```

If PowerShell blocks unsigned scripts, run:

```bat
tools\build\Build_Portable_Windows_App.bat
```

If Python 3.14 `.venv` creation fails in `ensurepip`, use the local `.build-deps` workaround in `docs\WINDOWS_PORTABLE_BUILD.md`.

Confirm:

- `dist\HappyMeasure\HappyMeasure.exe` exists.
- `dist\HappyMeasure\_internal` exists.
- `README_FIRST.txt`, `HARDWARE_VALIDATION_PROTOCOL.md`, and `HARDWARE_DRY_RUN_GUIDE.md` are copied into `dist\HappyMeasure`.
- The packaged exe launches once and stays running.
- About/update-check UI opens without import errors.
- Debug simulator can connect and run one short sweep in the packaged app.

Zip the whole folder, not only the exe:

```powershell
Compress-Archive -Path dist\HappyMeasure -DestinationPath dist\HappyMeasure-<version>-windows-portable.zip -CompressionLevel Optimal
```

## 9. Git and GitHub release

Before tagging:

```powershell
git status --short
git log --oneline -5
```

Confirm the release commit contains source/docs/tests only, not `dist`, `build`, logs, caches, or local helper scripts.

Suggested tag pattern:

```powershell
git tag v<version>
git push origin main --tags
```

Create the GitHub Release:

- Use tag `v<version>`.
- Mark alpha/beta releases as prerelease.
- Upload `HappyMeasure-<version>-windows-portable.zip`.
- Include safety status: simulator validated, hardware validation level reached, and whether real-DUT validation is pending.
- State that the app checks release metadata only; users upgrade manually.

## 10. Post-release verification

After publishing:

- Open the release page and confirm the asset downloads.
- Start the previous local version and confirm the manual update reminder reports the new release when network is available.
- Confirm offline/no-network update checks remain non-blocking.
- Download the release zip to a fresh folder and launch `HappyMeasure.exe` once.
- Record final release status in `docs/CODEX_DIARY_TEMP.md` or the permanent changelog.
