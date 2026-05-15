from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def read(rel: str) -> str:
    return Path(rel).read_text(encoding="utf-8")


def test_default_font_is_verdana_and_font_combo_uses_system_fonts():
    assert 'ui_font_family: str = "Verdana"' in read('src/keith_ivt/data/settings.py')
    simple = read('src/keith_ivt/ui/simple_app.py')
    panels = read('src/keith_ivt/ui/panels.py')
    assert 'tkfont.families(self.root)' in simple
    assert 'tkfont.families(self.root)' in panels
    assert 'self._available_ui_fonts()' in panels
    assert '["San Francisco", "SF Pro Display"' not in panels


def test_trace_color_column_does_not_show_hex_code_and_tree_is_multiselect():
    plot_panel = read('src/keith_ivt/ui/plot_panel.py')
    trace_panel = read('src/keith_ivt/ui/trace_panel.py')
    assert 'selectmode="extended"' in plot_panel
    assert '"■",' in trace_panel
    assert 'f"■ {trace.color}"' not in trace_panel
    assert 'def _ensure_trace_selection' in trace_panel
    assert 'def _selected_trace_ids' in trace_panel
    assert '<<TreeviewSelect>>' in plot_panel


def test_selected_traces_are_highlighted_in_plot():
    plot_panel = read('src/keith_ivt/ui/plot_panel.py')
    assert 'selected_trace_ids = set(self._selected_trace_ids())' in plot_panel
    assert 'linewidth=2.4 if is_selected else 0.9' in plot_panel
    assert 'alpha=1.0 if is_selected else 0.35' in plot_panel


def test_log_rotation_applies_when_limit_is_lowered(tmp_path):
    from keith_ivt.data.logging_utils import AppLog

    log_path = tmp_path / 'logs' / 'log.txt'
    log = AppLog(path=log_path, max_bytes=100_000)
    log.write('x' * 5000)
    assert log_path.exists()
    log.set_max_bytes(1024)
    assert list(log_path.parent.glob('log_*.txt'))
    assert not log_path.exists() or log_path.stat().st_size <= 1024


def test_readme_contains_human_developer_handoff():
    readme = read('README.md')
    assert 'Human developer handoff' in readme
    assert '0.7a1' in readme
    assert 'Real hardware preflight' in readme
