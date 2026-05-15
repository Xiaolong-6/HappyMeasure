from __future__ import annotations

from types import SimpleNamespace

from keith_ivt.data.dataset_store import DatasetStore
from keith_ivt.models import SweepConfig, SweepMode, SweepPoint, SweepResult
from keith_ivt.ui.trace_controls import TraceInteractionMixin
from keith_ivt.ui.trace_panel import TracePanelMixin


class FakeTree:
    def __init__(self) -> None:
        self._items: list[str] = []
        self._selection: list[str] = []
        self._values: dict[str, tuple] = {}
        self._row_at_y: dict[int, str] = {}

    def selection(self): return tuple(self._selection)
    def selection_set(self, items):
        if isinstance(items, str):
            self._selection = [items]
        else:
            self._selection = list(items)
    def delete(self, *items):
        for item in items:
            if item in self._items:
                self._items.remove(item)
        self._selection = [item for item in self._selection if item in self._items]
    def get_children(self): return tuple(self._items)
    def insert(self, parent, index, values=(), tags=()):
        item = f"I{len(self._items) + 1}"
        self._items.append(item)
        self._values[item] = values
        self._row_at_y[len(self._items)] = item
        return item
    def tag_configure(self, *args, **kwargs): pass
    def identify_row(self, y): return self._row_at_y.get(y, "")
    def identify_column(self, x): return "#3"
    def column(self, *args, **kwargs): pass


class DummyTraceApp(TracePanelMixin, TraceInteractionMixin):
    def __init__(self) -> None:
        self._datasets = DatasetStore()
        self.trace_tree = FakeTree()
        self._tree_item_to_trace = {}
        self.trace_column_vars = {}
        self._trace_columns = {}
        self._selected_trace_id = None
        self.root = None
        self.ui_font_family = SimpleNamespace(get=lambda: "Verdana")
        self.ui_font_size = SimpleNamespace(get=lambda: 10)
        self.events: list[str] = []
        self.redraws = 0
    def _redraw_all_plots(self): self.redraws += 1
    def log_event(self, message): self.events.append(message)
    def view_selected_trace_data(self): pass
    def save_selected_trace(self): pass
    def save_checked_traces(self): pass
    def save_all_traces(self): pass
    def import_csv(self): pass
    def rename_selected_trace(self): pass
    def choose_selected_trace_color(self): pass
    def toggle_selected_trace_visibility(self): pass
    def clear_all_traces(self): pass


def _result(name: str) -> SweepResult:
    cfg = SweepConfig(mode=SweepMode.VOLTAGE_SOURCE, start=0, stop=1, step=1, compliance=0.01, nplc=0.1, device_name=name)
    return SweepResult(cfg, [SweepPoint(0.0, 0.0)])


def test_delete_selected_trace_removes_all_selected_rows_and_preserves_one_selection() -> None:
    app = DummyTraceApp()
    for name in ["A", "B", "C"]:
        app._datasets.add_result(_result(name), name=name)
    app._refresh_trace_list()
    items = list(app.trace_tree.get_children())
    ids_by_item = dict(app._tree_item_to_trace)
    app.trace_tree.selection_set(items[:2])

    assert app.delete_selected_trace(SimpleNamespace()) == "break"

    remaining_ids = {trace.trace_id for trace in app._datasets.all()}
    assert ids_by_item[items[0]] not in remaining_ids
    assert ids_by_item[items[1]] not in remaining_ids
    assert ids_by_item[items[2]] in remaining_ids
    assert len(app.trace_tree.selection()) == 1
    assert "Deleted 2 selected traces." in app.events


def test_right_click_on_selected_row_preserves_multi_selection(monkeypatch) -> None:
    app = DummyTraceApp()
    for name in ["A", "B", "C"]:
        app._datasets.add_result(_result(name), name=name)
    app._refresh_trace_list()
    items = list(app.trace_tree.get_children())
    app.trace_tree.selection_set(items[:2])

    class Menu:
        def add_command(self, *a, **k): pass
        def add_separator(self): pass
        def add_cascade(self, *a, **k): pass
        def add_checkbutton(self, *a, **k): pass
    monkeypatch.setattr("keith_ivt.ui.trace_controls.make_touch_menu", lambda *a, **k: Menu())
    monkeypatch.setattr("keith_ivt.ui.trace_controls.popup_menu", lambda *a, **k: None)

    app._show_trace_context_menu(SimpleNamespace(y=1, x_root=10, y_root=20))
    assert list(app.trace_tree.selection()) == items[:2]
