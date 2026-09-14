# AGENTS.md

## Project

HappyMeasure is hardware-facing measurement software. Changes must prioritize measurement correctness, operator safety, recoverability and regression resistance over code simplification.

The public namespace is `happymeasure`. The historical internal/compatibility namespace is `keith_ivt`; do not rename it opportunistically.

## Read first

For non-trivial work, read the owner documents relevant to the change:

- `docs/ARCHITECTURE_CURRENT.md`
- `docs/STATE_MACHINE.md`
- `docs/VALIDATION_STATUS.md`
- `docs/RELEASE_CHECKLIST.md`
- `docs/VERSIONING.md`
- `docs/ERROR_RECOVERY.md`
- `docs/HARDWARE_VALIDATION_PROTOCOL.md`
- `docs/README.md`
- `CONTRIBUTING.md`

Do not create chronological agent diaries. Put stable contracts in owner documents, release history in the changelog/release record, and current gate semantics in `VALIDATION_STATUS.md`.

## Architecture boundaries

Keep these ownership boundaries intact unless the task explicitly requires an architectural change:

- `src/keith_ivt/ui/simple_app.py`: composition root; keep feature logic out.
- `src/keith_ivt/ui/sweep_controller.py`: Start/Pause/Stop, worker lifecycle, queue and completion/error orchestration.
- `src/keith_ivt/ui/app_state.py`: authoritative run/connection state machine.
- `src/keith_ivt/core/sweep_runner.py`: measurement execution/timing.
- `src/keith_ivt/services/measurement_service.py`: driver/service boundary.
- `src/keith_ivt/models.py`: sweep configuration/value generation/validation.
- `src/keith_ivt/data/dataset_store.py`: authoritative trace registry.
- `src/map_reconstruction/project_io.py`: `.hmmap` persistence contract.

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
11. GUI Detect COM must not guess baud rates or send SCPI.

## Tests

For each bug fix, reproduce the failure where practical, fix the root cause, run focused tests and then the broader gate appropriate to the touched boundary.

A release candidate requires the full source suite plus the dedicated Map Qt gate described in `docs/RELEASE_CHECKLIST.md`. Do not count dependency-driven `importorskip` as a passed Map release gate.

Do not weaken coverage thresholds or delete meaningful regressions merely to make CI green.

## Documentation and privacy

Every code change must consider documentation. Use `docs/README.md` to find the owner document. Avoid duplicating the same procedure into multiple files.

Never commit workstation-specific absolute home paths, local usernames, private local directory layouts, or physical instrument serial numbers. Use relative paths, environment variables or clearly synthetic identifiers in tests/examples.

## Version discipline

Every commit increments the internal beta serial by exactly one relative to its first parent and keeps `src/keith_ivt/version.py` and `pyproject.toml` consistent. This applies to code, tests and documentation-only commits. CI enforces the sequence across the whole pushed/PR commit range.

The final public release version/tag is selected by a human after the release audit. Internal build numbering is not itself the public release decision.

## Git workflow

Unless explicitly instructed otherwise:

- work on a dedicated branch;
- do not merge into `main`;
- keep commits focused;
- bump the internal build version in every commit;
- report branch, commit SHA, changed files, tests and remaining risks.
