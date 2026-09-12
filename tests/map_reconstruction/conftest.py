from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def fail_on_unexpected_modal_dialog(monkeypatch):
    """Keep the offscreen Map suite non-interactive.

    Tests that intentionally exercise a dialog must monkeypatch the specific
    dialog API themselves. Any other modal/file dialog is a test bug (and
    would otherwise hang the Windows CI runner indefinitely).
    """

    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets

    def unexpected(*_args, **_kwargs):
        raise AssertionError(
            "Unexpected modal dialog in offscreen Map test; mock the explicit "
            "operator choice in this test."
        )

    monkeypatch.setattr(QtWidgets.QMessageBox, "exec", unexpected)
    for name in ("information", "warning", "critical", "question"):
        monkeypatch.setattr(QtWidgets.QMessageBox, name, staticmethod(unexpected))

    for name in ("getOpenFileName", "getSaveFileName", "getExistingDirectory"):
        monkeypatch.setattr(QtWidgets.QFileDialog, name, staticmethod(unexpected))
