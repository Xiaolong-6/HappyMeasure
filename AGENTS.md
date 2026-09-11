# AGENTS.md

## Project

HappyMeasure is hardware-facing measurement software. Changes must prioritize measurement correctness, operator safety, recoverability and regression resistance over code simplification.

The public namespace is `happymeasure`. The historical internal/compatibility namespace is `keith_ivt`; do not rename it opportunistically.

## Read first

For non-trivial work, read the owner documents relevant to the change:

- `docs/ARCHITECTURE_CURRENT.md` — current architecture
- `docs/STATE_MACHINE.md` — run/connection state model
- `docs/VALIDATION_STATUS.md` — current release/test status
- `CONTRIBUTING.md` — documentation and validation requirements
- `docs/RELEASE_CHECKLIST.md` — release validation
- `docs/ERROR_RECOVERY.md` — recovery behavior
- `docs/HARDWARE_VALIDATION_PROTOCOL.md` — real-hardware validation
- `docs/README.md` — documentation ownership/index

Do not create chronological agent diaries. Put stable contracts in their owner document, release history in the changelog/release notes, and current gate status in `VALIDATION_STATUS.md`.

## Architecture boundaries

Keep these ownership boundaries intact unless the task explicitly requires an architectural change:

- `src/keith_ivt/ui/simple_app.py`: composition root; keep feature logic out.
- `src/keith_ivt/ui/sweep_controller.py`: Start/Pause/Stop, worker lifecycle, queue and completion/error orchestration.
- `src/keith_ivt/ui/app_state.py`: authoritative run/connection state machine.
- `src/keith_ivt/core/sweep_runner.py`: current Tk measurement execution boundary.
- `src/keith_ivt/services/measurement_service.py`: driver/service boundary.
- `src/keith_ivt/models.py`: sweep configuration/value generation/validation.
- `src/keith_ivt/data/dataset_store.py`: authoritative trace registry.
- `src/map_reconstruction/project_io.py`: `.hmmap` persistence contract; derived maps are not authoritative source data.

## Safety invariants

1. Validate before enabling output whenever possible.
2. Runtime measurement failures must attempt a safe output state.
3. Do not remove/weaken `finally` / `output_off()` paths.
4. User Stop must shut down output even if normal completion may leave it enabled.
5. Recoverable errors must not require restarting HappyMeasure.
6. Pause/Stop must remain responsive during fast acquisition.
7. Do not restore unbounded UI queue draining or redraw per queued point.
8. Do not read Tk variables from worker threads; create immutable configuration snapshots on the UI thread.
9. Display reduction/windowing must never truncate saved scientific data.
10. Simulator/CI success is never proof of real-hardware compatibility.

## State and validation rules

`AppState` is authoritative. Ready-to-start states include `idle`, `stopped`, `completed` and `aborted`. State transitions go through `AppAction` / `AppState`.

Prefer one canonical parameter/model validation implementation. User input errors should be concise operator-facing messages; internal tracebacks belong in logs/diagnostics.

## Tests

For each bug fix, reproduce the failure where practical, fix the root cause, run the focused tests and then the broader gate appropriate to the touched boundary.

A release candidate requires the full source suite plus the dedicated Map Qt gate described in `docs/RELEASE_CHECKLIST.md`. Do not count a dependency-driven `importorskip` as a passed Map release gate.

Do not weaken coverage thresholds or delete a meaningful regression merely to make CI green. A test may be removed/consolidated only when its behavior is obsolete or already covered by a stronger test, with that rationale recorded in the change.

## Documentation

Every code change must consider documentation. Use `docs/README.md` to find the owner document. Avoid duplicating the same procedure into multiple files.

## Git workflow

Unless explicitly instructed otherwise:

- work on a dedicated branch;
- do not merge into `main`;
- keep commits focused;
- report branch, commit SHA, changed files, tests and remaining risks.

Do not alter release/version metadata in an ordinary bug fix unless the task explicitly prepares a release.
