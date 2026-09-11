# Troubleshooting

Start with the repository diagnostics runner:

```powershell
tools\diagnostics\Run_Diagnostics.bat
```

It writes `logs/diagnostics_report.txt`. Useful runtime logs are:

```text
logs/log.txt
logs/error.log
logs/console_last_run.log
```

## Launch/import problems

If the app cannot import `keith_ivt`, use `Run_HappyMeasure.bat` or `Run_HappyMeasure.ps1` from the repository root. The maintained launchers set the source path correctly and handle project paths containing spaces. Avoid hand-written unquoted Windows paths.

## Restart UI

**Settings → Restart UI** asks for confirmation, starts a detached replacement process, then closes the current UI.

Current behavior:

- source/development launch (`sys.argv[0]` ends in `.py`): restart with the current Python interpreter and script;
- packaged executable/launcher path: restart the current executable/entry path;
- current command-line arguments are preserved;
- unsaved UI changes are not preserved;
- on failure, the existing process stays responsible for showing a restart error and the user should restart manually.

The restart action is convenience only; it is not a project-save mechanism and must not be used as an error-recovery substitute while a measurement is active.

## Windows portable build

The normal portable build uses Python 3.12, 3.11, or 3.13. Python 3.14 has a separate maintained packaging path because some Windows/Python 3.14 environments have shown temporary-directory and pytest-cleanup issues.

Use:

```text
tools\build\Build_Portable_Windows_App_Python314.bat
```

or the matching PowerShell script when building specifically with Python 3.14. See `WINDOWS_PORTABLE_BUILD.md` for the common packaging contract and `WINDOWS_PYTHON314_BUILD.md` only for the 3.14-specific differences/workaround.

If PowerShell execution policy blocks a `.ps1` build launcher, use the corresponding `.bat` launcher.

## Hardware connection problems

Do not troubleshoot a first connection by starting a sweep. Run the output-off-only preflight described in `HARDWARE_PREFLIGHT.md`, then follow `HARDWARE_VALIDATION_PROTOCOL.md`. A simulator pass is not evidence of real-hardware safety.
