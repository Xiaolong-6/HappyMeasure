from pathlib import Path

from keith_ivt.diagnostics.runtime_logging import TeeTextIO

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_plot_range_dialog_is_scheduled_after_context_menu_returns():
    plot_controls = read("src/keith_ivt/ui/plot_controls.py")
    assert "command=lambda a=ax: self._schedule_axis_range_dialog(axis=\"x\", ax=a)" in plot_controls
    assert "command=lambda a=ax: self._schedule_axis_range_dialog(axis=\"y\", ax=a)" in plot_controls
    assert "def _schedule_axis_range_dialog" in plot_controls
    assert "self.root.after(250" in plot_controls
    assert "simpledialog" not in plot_controls
    # Do not use aggressive focus/menu hacks: they caused a persistent menu
    # artifact and collapsed the hover dock on Windows/Tk packaged builds.
    assert "focus_force" not in plot_controls
    assert "self.root.update()" not in plot_controls
    assert "tk::MenuUnpost" not in plot_controls


def test_axis_range_dialog_uses_custom_toplevel_editor():
    plot_controls = read("src/keith_ivt/ui/plot_controls.py")
    assert "win = Toplevel(self.root)" in plot_controls
    assert "win.title(\"Set axis range\")" in plot_controls
    assert "ttk.Entry" in plot_controls
    assert "_apply_axis_range_text" in plot_controls
    assert "messagebox.showerror(\"Invalid axis range\", str(exc), parent=win)" in plot_controls


def test_runtime_tee_handles_missing_original_stream(tmp_path):
    log_path = tmp_path / "console.log"
    with log_path.open("w", encoding="utf-8") as fh:
        tee = TeeTextIO(None, fh)
        assert tee.write("hello\n") == 6
        tee.flush()
    assert log_path.read_text(encoding="utf-8") == "hello\n"
