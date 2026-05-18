from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_plot_canvas_has_drag_and_hover_event_hooks():
    panel = read("src/keith_ivt/ui/plot_panel.py")
    assert 'button_release_event", self._on_mpl_plot_release' in panel
    assert 'motion_notify_event", self._on_mpl_plot_motion' in panel
    assert 'self._start_plot_pan(event)' in panel
    assert 'def _drag_pan_plot' in panel
    assert 'ax.set_xlim' in panel
    assert 'ax.set_ylim' in panel


def test_plot_hover_uses_nearest_visible_point_annotation():
    panel = read("src/keith_ivt/ui/plot_panel.py")
    assert 'def _nearest_visible_plot_point' in panel
    assert 'max_distance_px: float = 14.0' in panel
    assert 'line.get_xdata(orig=False)' in panel
    assert 'line.get_ydata(orig=False)' in panel
    assert 'ax.annotate' in panel
    assert 'X: {self._format_hover_value(x)}' in panel
    assert 'Y: {self._format_hover_value(y)}' in panel


def test_plot_interaction_state_resets_on_redraw():
    panel = read("src/keith_ivt/ui/plot_panel.py")
    assert 'self._plot_hover_annotation = None' in panel
    assert 'self._plot_pan_state = None' in panel
