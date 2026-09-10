"""Three-stage navigation header for the Map Reconstruction application."""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets  # type: ignore[import-not-found]


class WorkflowHeader(QtWidgets.QWidget):
    stageSelected = QtCore.Signal(int)
    openCsvRequested = QtCore.Signal()
    openProjectRequested = QtCore.Signal()
    saveRequested = QtCore.Signal()
    exportRequested = QtCore.Signal()
    exportPreparedRequested = QtCore.Signal()
    exportRawRequested = QtCore.Signal()
    exportProcessedRequested = QtCore.Signal()
    exportBothRequested = QtCore.Signal()
    exportSummaryRequested = QtCore.Signal()
    exportPdfRequested = QtCore.Signal()

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
        self.open_button = QtWidgets.QPushButton("Open")
        self.open_button.setObjectName("headerAction")
        self.open_button.setToolTip("Open HappyMeasure CSV")
        self.open_button.setMinimumWidth(58)
        self.open_button.clicked.connect(self.openCsvRequested)
        action_row.addWidget(self.open_button)

        self.project_button = QtWidgets.QPushButton("Project")
        self.project_button.setObjectName("headerAction")
        self.project_button.setToolTip("Open a saved project")
        self.project_button.setMinimumWidth(58)
        self.project_button.clicked.connect(self.openProjectRequested)
        action_row.addWidget(self.project_button)

        self.save_button = QtWidgets.QPushButton("Save")
        self.save_button.setObjectName("headerAction")
        self.save_button.setToolTip("Save project")
        self.save_button.setMinimumWidth(58)
        self.save_button.clicked.connect(self.saveRequested)
        action_row.addWidget(self.save_button)

        self.export_button = QtWidgets.QPushButton("Export")
        self.export_button.setObjectName("headerAction")
        self.export_button.setToolTip("Export prepared data, maps, summary, or PDF")
        self.export_button.setMinimumWidth(58)
        self.export_menu = QtWidgets.QMenu(self.export_button)
        self.prepared_action = self.export_menu.addAction("Prepared time trace")
        self.raw_action = self.export_menu.addAction("Raw reconstructed map")
        self.processed_action = self.export_menu.addAction("Processed map")
        self.both_action = self.export_menu.addAction("Both maps")
        self.export_menu.addSeparator()
        self.summary_action = self.export_menu.addAction("Parameter summary")
        self.pdf_action = self.export_menu.addAction("PDF report")
        self.prepared_action.triggered.connect(self.exportPreparedRequested)
        self.raw_action.triggered.connect(self.exportRawRequested)
        # Keep the historical processed-export signal as the canonical path so
        # the existing composition root does not open two dialogs.
        self.processed_action.triggered.connect(self.exportRequested)
        self.both_action.triggered.connect(self.exportBothRequested)
        self.summary_action.triggered.connect(self.exportSummaryRequested)
        self.pdf_action.triggered.connect(self.exportPdfRequested)
        self.export_button.setMenu(self.export_menu)
        action_row.addWidget(self.export_button)

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
        self.set_action_availability(False, False, False, False)

    def set_filename(self, filename: str | None) -> None:
        self.file_label.setText(filename or "No source loaded")

    def set_status(self, prepared: bool, reconstructed: bool, analyzed: bool) -> None:
        for label, value, name in (
            (self.prepared_status, prepared, "Prepared"),
            (self.reconstructed_status, reconstructed, "Reconstructed"),
            (self.analyzed_status, analyzed, "Analyzed"),
        ):
            label.setText(f"{name} {'✓' if value else '—'}")

    def set_action_availability(
        self,
        source_available: bool,
        prepared_available: bool,
        raw_available: bool,
        processed_available: bool,
    ) -> None:
        """Keep global actions aligned with the currently reproducible workspace state."""

        self.save_button.setEnabled(source_available)
        self.prepared_action.setEnabled(prepared_available)
        self.raw_action.setEnabled(raw_available)
        self.processed_action.setEnabled(processed_available)
        self.both_action.setEnabled(raw_available and processed_available)
        self.summary_action.setEnabled(source_available)
        self.pdf_action.setEnabled(raw_available)
        self.export_button.setEnabled(
            prepared_available or raw_available or processed_available or source_available
        )
