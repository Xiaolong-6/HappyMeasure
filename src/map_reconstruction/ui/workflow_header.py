"""Three-stage navigation header for the Map Reconstruction application."""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets  # type: ignore[import-not-found]


class WorkflowHeader(QtWidgets.QWidget):
    stageSelected = QtCore.Signal(int)
    openCsvRequested = QtCore.Signal()
    openProjectRequested = QtCore.Signal()
    saveRequested = QtCore.Signal()
    exportRequested = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("workflowHeader")
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        top = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("Map Reconstruction")
        title.setObjectName("appTitle")
        top.addWidget(title)
        self.file_label = QtWidgets.QLabel("No source loaded")
        self.file_label.setObjectName("workflowFile")
        top.addWidget(self.file_label, 1)
        self.prepared_status = QtWidgets.QLabel("Prepared —")
        self.reconstructed_status = QtWidgets.QLabel("Reconstructed —")
        self.analyzed_status = QtWidgets.QLabel("Analyzed —")
        for label in (self.prepared_status, self.reconstructed_status, self.analyzed_status):
            label.setObjectName("workflowStatus")
            top.addWidget(label)
        action_row = QtWidgets.QHBoxLayout()
        action_row.addStretch(1)
        for text, tooltip, signal in (
            ("Open", "Open HappyMeasure CSV", self.openCsvRequested),
            ("Project", "Open a saved project", self.openProjectRequested),
            ("Save", "Save project", self.saveRequested),
            ("Export", "Export map", self.exportRequested),
        ):
            button = QtWidgets.QPushButton(text)
            button.setObjectName("headerAction")
            button.setToolTip(tooltip)
            button.setMinimumWidth(58)
            button.clicked.connect(signal)
            action_row.addWidget(button)
        root.addLayout(top)
        root.addLayout(action_row)
        nav = QtWidgets.QHBoxLayout()
        self.stage_buttons: list[QtWidgets.QPushButton] = []
        for index, text in enumerate(("1  Preparation", "2  Reconstruction", "3  Analysis")):
            button = QtWidgets.QPushButton(text)
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.clicked.connect(
                lambda _checked=False, value=index: self.stageSelected.emit(value)
            )
            nav.addWidget(button)
            self.stage_buttons.append(button)
        self.stage_buttons[0].setChecked(True)
        nav.addStretch(1)
        root.addLayout(nav)

    def set_filename(self, filename: str | None) -> None:
        self.file_label.setText(filename or "No source loaded")

    def set_status(self, prepared: bool, reconstructed: bool, analyzed: bool) -> None:
        for label, value, name in (
            (self.prepared_status, prepared, "Prepared"),
            (self.reconstructed_status, reconstructed, "Reconstructed"),
            (self.analyzed_status, analyzed, "Analyzed"),
        ):
            label.setText(f"{name} {'✓' if value else '—'}")
