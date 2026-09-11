# Test suite ownership

The suite has three explicit owners:

```text
tests/
  happymeasure/        HappyMeasure (`keith_ivt` / public `happymeasure`) behavior
  map_reconstruction/  Map Reconstruction behavior
  common/              repository-wide release/build/namespace contracts
  conftest.py           shared test bootstrap only
  run_full_validation.py
  README.md
```

`common/` is intentionally narrow. It is for repository-level packaging, launchers, versioning, namespace migration, documentation/release integrity, and shared build infrastructure; it is not a miscellaneous bucket.

## Test quality rules

- Prefer observable behavior and public/semi-public contracts over Python source-text matching.
- Do not assert comments, private helper names, exact import structure, or arbitrary widget implementation details unless the text/script itself is the supported artifact.
- A regression belongs with the subsystem it protects. Do not create `legacy`, `followup`, `handoff`, `closeout`, `polish`, `quick_fix`, or `extra coverage` bucket files.
- Keep one canonical owner for each behavior; delete weaker duplicate coverage.
- UI smoke tests may be environment-gated, but source grep is not a substitute for exercising the UI lifecycle.
- Real hardware remains a separate bench gate and must never be implied by a passing software-only suite.

## Gates

```text
python -m pytest -q
python -m pytest tests/happymeasure -q
python -m pytest tests/map_reconstruction -q
python -m pytest tests/common -q
python tests/run_full_validation.py
```

Optional Windows desktop smoke test:

```powershell
$env:HAPPYMEASURE_RUN_TK_SMOKE="1"
python -m pytest tests/happymeasure/test_ui_smoke.py -q
```

## Hardware gate before release

- Real Windows Tk smoke test.
- Real serial preflight: `python -m happymeasure.hardware_preflight COMx --baud 9600`.
- Dummy-load STEP sweep.
- Constant-time stop test.
- Error-path test with disconnected serial cable only after confirming output-off behavior on dummy load.
