# Test suite ownership

The suite has two explicit owners:

```text
tests/
  happymeasure/        HappyMeasure (`keith_ivt` / public `happymeasure`) behavior
  common/              repository-wide release/build/namespace contracts
  conftest.py          shared test bootstrap only
  run_full_validation.py
  README.md
```

`common/` is intentionally narrow. It is for repository-level packaging, launchers, versioning, namespace/documentation/release integrity, and shared build infrastructure; it is not a miscellaneous bucket.

Browser Map Reconstruction and IV Fitter have independent test suites in their own repositories.

## Test quality rules

- Prefer observable behavior and public/semi-public contracts over Python source-text matching.
- Do not assert comments, private helper names, exact import structure, or arbitrary widget implementation details unless the text/script itself is the supported artifact.
- A regression belongs with the subsystem it protects. Do not create `legacy`, `followup`, `handoff`, `closeout`, `polish`, `quick_fix`, or `extra coverage` bucket files.
- Keep one canonical owner for each behavior; delete weaker duplicate coverage.
- UI smoke tests may be environment-gated, but source grep is not a substitute for exercising the UI lifecycle.
- Real hardware remains a separate bench gate and must never be implied by a passing software-only suite.

## Core gate (`.[dev]`)

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q tests/common tests/happymeasure
python -m pytest tests/common tests/happymeasure --cov=keith_ivt --cov-report=term -q
```

`python tests/run_full_validation.py` is the complete local source-validation entry point.

Optional Windows desktop Tk smoke:

```powershell
$env:HAPPYMEASURE_RUN_TK_SMOKE="1"
python -m pytest tests/happymeasure/test_ui_smoke.py -q
```

## Hardware gate before release

After source/desktop gates pass, follow `docs/HARDWARE_VALIDATION_PROTOCOL.md`: no-DUT preflight first, then a known dummy load, then any real DUT. Confirm physical Output OFF after the required completion/Stop/error/disconnect paths.
