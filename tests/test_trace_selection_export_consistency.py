from __future__ import annotations

from types import SimpleNamespace

from keith_ivt.data.dataset_store import DatasetStore
from keith_ivt.models import SweepConfig, SweepMode, SweepPoint, SweepResult
from keith_ivt.ui import trace_panel as trace_panel_module
from keith_ivt.ui.trace_panel import TracePanelMixin


class FakeTree:
    def __init__(self) -> None:
        self._items: list[str] = []
        self._selection: list[str] = []
        self._values: dict[str, tuple] = {}

    def selection(self):
        return tuple(self._selection)

    def selection_set(self, items):
        if isinstance(items, str):
            self._selection = [items]
        else:
            self._selection = [item for item in items if item in self._items]

    def delete(self, *items):
        for item in items:
            if item in self._items:
                self._items.remove(item)
        self._selection = [item for item in self._selection if item in self._items]

    def get_children(self):
        return tuple(self._items)

    def insert(self, parent, index, values=(), tags=()):
        item = f"I{len(self._items) + 1}"
        self._items.append(item)
        self._values[item] = values
        return item

    def tag_configure(self, *args, **kwargs):
        pass

    def column(self, *args, **kwargs):
        pass


class DummyVar:
    def __init__(self, value="") -> None:
        self.value = value

    def set(self, value):
        self.value = value

    def get(self):
        return self.value


class DummyTraceApp(TracePanelMixin):
    def __init__(self) -> None:
        self._datasets = DatasetStore()
        self.trace_tree = FakeTree()
        self._tree_item_to_trace = {}
        self.trace_column_vars = {}
        self._trace_columns = {}
        self._selected_trace_id = None
        self.trace_title_text = DummyVar()
        self.last_save_text = DummyVar()
        self.events: list[str] = []
        self.redraws = 0
        self.marked_saves: list[str] = []

    def _redraw_all_plots(self):
        self.redraws += 1

    def log_event(self, message):
        self.events.append(message)

    def _mark_last_save(self, action: str = "save") -> None:
        self.marked_saves.append(action)


def _result(name: str, value: float = 0.0) -> SweepResult:
    cfg = SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0,
        stop=1,
        step=1,
        compliance=0.01,
        nplc=0.1,
        device_name=name,
    )
    return SweepResult(cfg, [SweepPoint(value, value * 1e-3)])


def test_delete_last_trace_clears_selected_trace_id_and_tree_selection() -> None:
    app = DummyTraceApp()
    app._datasets.add_result(_result("Only"), name="Only")
    app._refresh_trace_list()
    assert app._selected_trace_id is not None
    assert app.trace_tree.selection()

    assert app.delete_selected_trace(SimpleNamespace()) == "break"

    assert app._selected_trace_id is None
    assert app.trace_tree.selection() == ()
    assert app.trace_tree.get_children() == ()
    assert app.trace_title_text.get() == "Traces (0)"


def test_stale_selected_trace_id_is_ignored_after_external_delete() -> None:
    app = DummyTraceApp()
    first = app._datasets.add_result(_result("A"), name="A")
    second = app._datasets.add_result(_result("B"), name="B")
    app._refresh_trace_list()
    app._selected_trace_id = first.trace_id
    app._datasets.remove(first.trace_id)

    app._refresh_trace_list()

    assert app._selected_trace_id == second.trace_id
    assert app._selected_trace() is not None
    assert app._selected_trace().trace_id == second.trace_id


def test_rename_then_save_all_exports_edited_trace_name(monkeypatch) -> None:
    app = DummyTraceApp()
    trace = app._datasets.add_result(_result("Original"), name="Original")
    app._datasets.rename(trace.trace_id, "EditedDevice")
    captured: dict[str, object] = {}

    monkeypatch.setattr(trace_panel_module.filedialog, "asksaveasfilename", lambda **_kwargs: "combined.csv")

    def fake_save_combined_csv(results, path):
        captured["names"] = [result.config.device_name for result in results]
        captured["path"] = path

    monkeypatch.setattr(trace_panel_module, "save_combined_csv", fake_save_combined_csv)

    assert app.save_all_traces() is True

    assert captured["path"] == "combined.csv"
    assert captured["names"] == ["EditedDevice"]
    assert app.marked_saves == ["all CSV"]


def test_save_all_includes_hidden_traces_but_visible_export_filters_them(monkeypatch) -> None:
    app = DummyTraceApp()
    hidden = app._datasets.add_result(_result("Hidden", 1.0), name="Hidden")
    visible = app._datasets.add_result(_result("Visible", 2.0), name="Visible")
    app._datasets.toggle_visibility(hidden.trace_id)
    captured: list[list[str]] = []

    monkeypatch.setattr(trace_panel_module.filedialog, "asksaveasfilename", lambda **_kwargs: "out.csv")

    def fake_save_combined_csv(results, path):
        captured.append([result.config.device_name for result in results])

    monkeypatch.setattr(trace_panel_module, "save_combined_csv", fake_save_combined_csv)

    assert app.save_all_traces() is True
    assert app.save_checked_traces() is True

    assert captured[0] == ["Visible", "Hidden"]
    assert captured[1] == ["Visible"]
