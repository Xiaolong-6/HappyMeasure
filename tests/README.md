# HappyMeasure test map

This folder is organized by behavior, not by historical alpha number. Use this file when continuing work across agents/sessions.

## Main gates

```text
python tests/run_full_validation.py
python -m pytest -q
```

Optional Windows desktop smoke test:

```powershell
$env:HAPPYMEASURE_RUN_TK_SMOKE="1"
python -m pytest tests/test_ui_smoke.py -q
```

## Hardware gate before release

- Real Windows Tk smoke test.
- Real serial preflight: `python -m happymeasure.hardware_preflight COMx --baud 9600`.
- Dummy-load STEP sweep.
- Constant-time stop test.
- Error-path test with disconnected serial cable only after confirming output-off behavior on dummy load.

## Coverage note

The coverage configuration now includes `services/` and `drivers/` rather than omitting all of them. Hardware-only branches still need mock/fake serial coverage. Coverage gate: `python -m pytest --cov=keith_ivt -q` must pass >=95% for the unit-testable core/hardware subset; Tk widgets and real hardware entrypoints are excluded and covered by smoke/bench protocols.

## Behavior-oriented files

```text
test_legacy_ui_layout_contracts.py   historical source/UI contracts from older alpha line
test_ui_simulator_refinements.py     simulator and UI refinement contracts
test_ui_interaction_polish.py        plot/trace/menu interaction contracts
test_theme_adaptive_layout.py        theme and adaptive-layout contracts
test_plot_connection_regression.py   plot/connection regression contracts
test_visual_responsive_layout.py     responsive layout contracts
test_navigation_theme_polish.py      navigation and theme polish contracts
test_theme_trace_menu.py             theme + trace context menu contracts
test_adaptive_log_settings.py        adaptive editor and log settings contracts
test_export_log_ui.py                export/log UI contracts
test_pause_adaptive_sweep.py         pause and adaptive sweep contracts
test_handoff_trace_log_font.py       latest trace/log/font handoff contracts
```

Core module tests keep direct names, for example `test_app_state.py`, `test_plot_performance.py`, `test_settings_v2.py`, and `test_hardware_abstraction.py`.


## Pre-hardware gates

- `test_version_consistency.py`: prevents runtime/pyproject/docs validation drift.
- `test_pre_hardware_safety.py`: verifies output-off behavior on key software failure/stop paths.
- `test_mock_visa_command_sequence.py`: records fake serial commands and compares intended Keithley 2400 source/measure setup.
- `test_trace_multi_delete.py`: verifies multi-select delete behavior without requiring a Tk desktop.
- Coverage gate: `python -m pytest --cov=keith_ivt -q` must pass >=95% for the unit-testable core/hardware subset; Tk widgets and real hardware entrypoints are excluded and covered by smoke/bench protocols.
