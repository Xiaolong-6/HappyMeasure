from __future__ import annotations

import builtins

import pytest

from map_reconstruction import __main__ as entrypoint


def test_entrypoint_reports_only_missing_optional_gui_dependencies(monkeypatch, capsys) -> None:
    original_import = builtins.__import__

    def missing_gui(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "map_reconstruction.ui.main_window":
            raise ModuleNotFoundError("No module named 'pyqtgraph'", name="pyqtgraph")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", missing_gui)

    assert entrypoint.main([]) == 2
    assert "Missing: pyqtgraph" in capsys.readouterr().err


def test_entrypoint_does_not_disguise_internal_import_errors(monkeypatch) -> None:
    original_import = builtins.__import__

    def broken_application_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "map_reconstruction.ui.main_window":
            raise ImportError("unexpected application import failure")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", broken_application_import)

    with pytest.raises(ImportError, match="unexpected application import failure"):
        entrypoint.main([])
