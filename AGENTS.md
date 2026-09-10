# AGENTS.md

## Project

HappyMeasure is hardware-facing measurement software for source-measure
instruments. Changes must prioritize measurement correctness, operator safety,
recoverability, and regression resistance over code simplification.

The historical internal Python namespace is `keith_ivt`. Do not rename or
migrate it opportunistically.

## Read First

Before making non-trivial changes, inspect the relevant owner documents:

- `docs/ARCHITECTURE_CURRENT.md` — current architecture
- `docs/STATE_MACHINE.md` — run/connection state model
- `docs/AGENT_HANDOFF.md` — recent implementation context and known traps
- `CONTRIBUTING.md` — documentation and validation requirements
- `docs/RELEASE_CHECKLIST.md` — release validation
- `docs/ERROR_RECOVERY.md` — error/recovery behavior
- `docs/HARDWARE_VALIDATION_PROTOCOL.md` — real-hardware validation

Do not duplicate long procedures into this file. Update the owner document.

## Architecture Boundaries

Keep these ownership boundaries intact unless the task explicitly requires an
architectural change:

- `src/keith_ivt/ui/simple_app.py`: composition root; keep it small and do not
  accumulate feature logic here.
- `src/keith_ivt/ui/sweep_controller.py`: Start/Pause/Stop orchestration,
  worker lifecycle, UI queue processing, and sweep completion/error handling.
- `src/keith_ivt/ui/app_state.py`: authoritative run and connection state
  machine. State transitions must go through `AppAction` / `AppState`; do not
  invent parallel run-state flags.
- `src/keith_ivt/core/sweep_runner.py`: legacy Tk measurement execution
  boundary.
- `src/keith_ivt/services/measurement_service.py`: driver-level measurement
  service and future backend boundary.
- `src/keith_ivt/models.py`: sweep configuration and common sweep-value and
  validation logic.
- `src/keith_ivt/data/dataset_store.py`: authoritative trace registry.

## Safety Invariants

Treat these as hard requirements:

1. Configuration and validation errors must occur before instrument output is
   enabled whenever possible.
2. Runtime measurement failures must attempt to place the SMU in a safe output
   state.
3. Do not remove or weaken existing `finally` / `output_off()` safety paths.
4. User Stop must shut down output even when normal completion may leave output
   enabled.
5. An ordinary recoverable error must not require restarting HappyMeasure.
6. Pause and Stop must remain responsive during fast simulator or hardware
   acquisition.
7. Do not restore unbounded UI queue draining or redraw once per queued point.
8. Do not read Tk variables from worker threads. Build an immutable
   configuration snapshot on the UI thread.

## State-Machine Rules

`AppState` is authoritative. Ready-to-start states currently include `idle`,
`stopped`, `completed`, and `aborted`; do not regress Start gating to idle-only.

`ERROR` is a meaningful transient state. Recovery must use canonical AppState
transitions rather than directly mutating UI state. If changing state semantics,
update both state-machine tests and relevant UI status/button behavior.

## Validation Rules

Prefer one canonical validation implementation rather than duplicating
parameter checks in UI code, runners, and drivers. UI preflight should call
canonical model/service validation before starting a worker or touching
hardware.

User-input mistakes should produce concise operator-facing messages, not raw
tracebacks as the primary UI response. Internal tracebacks may remain available
through diagnostics and logging.

## Simulator and Fault Injection

The simulator is a deterministic development and regression tool.

- Normal simulator behavior must remain non-random.
- Fault profiles are for explicit tests only and must not be active by default.
- Keep simulator and hardware semantics aligned where practical.
- A simulator test passing is not proof of real-hardware compatibility.

## UI Rules

HappyMeasure targets Windows/Tk environments. Avoid forced-focus hacks,
unintended modal behavior, emoji-based status indicators, Tk access from worker
threads, and unnecessary redesign during bug fixes. Preserve Windows scaling
behavior when modifying layouts.

Keep fixes scoped. Do not mix unrelated visual redesign with measurement or
safety fixes.

## Tests

For every bug fix:

1. Reproduce the failure in a focused regression test where practical.
2. Fix the root cause.
3. Verify the regression test conceptually fails before and passes after.
4. Run the directly affected test group.
5. Run broader validation when changing shared measurement, state-machine,
   hardware, configuration, or packaging code.

Relevant suites commonly include:

- `tests/test_start_config_regression.py`
- `tests/test_sweep_safety.py`
- `tests/test_fault_injection_safety.py`
- `tests/test_app_state.py`
- `tests/test_hysteresis_sweep_values.py`
- `tests/test_error_handling.py`

### Map Reconstruction-only validation

For a change confined to `map_reconstruction` UI, visualization, or analysis
controls, validate the affected Map Reconstruction tests and offscreen Qt
regressions, then run Ruff, Black, mypy, and compileall only for the changed
Map Reconstruction sources. Measure `map_reconstruction` coverage separately.

Do not run the full HappyMeasure hardware/acquisition validation suite unless
the change touches shared modules, packaging/dependencies, or prepares a
repository release. Record Map Reconstruction and HappyMeasure validation
separately in `docs/TESTED_CURRENT.md`.

Before committing, also follow `CONTRIBUTING.md`. Do not weaken or delete a
regression test merely to make a change pass unless the tested behavior is
intentionally obsolete and that decision is documented.

## Documentation

Every code change must explicitly consider documentation. Follow
`CONTRIBUTING.md` and update the owner document instead of copying the same
procedure into several files.

Use `docs/AGENT_HANDOFF.md` for implementation context that future agents need
but that does not belong in permanent architecture documentation. Use
`docs/CHANGELOG.md` and release notes for historical changes rather than
expanding this file indefinitely.

## Change Discipline

For bug fixes, prefer the smallest complete fix, investigate adjacent instances
of the same root cause, avoid unrelated refactoring, preserve backward
compatibility unless a semantic change is intentional, and inspect the final
diff from a fresh perspective before committing.

Pay particular attention to hardware safety, state consistency, error recovery,
stale UI state, thread boundaries, persisted settings/preset compatibility, and
exported data compatibility.

## Git Workflow

Unless explicitly instructed otherwise:

- Work on a dedicated branch and do not merge into `main`.
- Keep commits focused and run relevant tests before committing.
- Report branch, commit SHA, files changed, tests run, and remaining risks.

Do not modify release/version metadata as part of an ordinary bug fix unless the
task explicitly requests a release.
