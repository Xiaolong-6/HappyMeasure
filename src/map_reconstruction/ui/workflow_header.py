"""Three-stage navigation header for the Map Reconstruction application."""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets  # type: ignore[import-not-found]

from map_reconstruction.ui.windows_shell import apply_windows_11_shell


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
        root.setSpacing(10)

        top = QtWidgets.QHBoxLayout()
        top.setContentsMargins(2, 0, 2, 0)
        top.setSpacing(12)
        title = QtWidgets.QLabel("Map Reconstruction")
        title.setObjectName("appTitle")
        top.addWidget(title)
        self.file_label = QtWidgets.QLabel("No source loaded")
        self.file_label.setObjectName("workflowFile")
        self.file_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self.file_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        top.addWidget(self.file_label, 1)
        root.addLayout(top)

        nav_host = QtWidgets.QFrame()
        nav_host.setObjectName("workflowNavigation")
        nav = QtWidgets.QHBoxLayout(nav_host)
        nav.setContentsMargins(4, 4, 4, 4)
        nav.setSpacing(4)
        self.stage_buttons: list[QtWidgets.QPushButton] = []
        labels = (
            "1   Signal Preparation",
            "2   Reconstruction",
            "3   Map Analysis",
        )
        for index, text in enumerate(labels):
            button = QtWidgets.QPushButton(text)
            button.setObjectName("workflowStage")
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            button.setMinimumHeight(36)
            button.setAccessibleName(text.replace("   ", " "))
            button.clicked.connect(
                lambda _checked=False, value=index: self.stageSelected.emit(value)
            )
            nav.addWidget(button, 1)
            self.stage_buttons.append(button)
        self.stage_buttons[0].setChecked(True)
        root.addWidget(nav_host)

        if parent is not None:
            # Delay the DWM request until the QMainWindow has finished creating
            # its central widget and native handle.  The helper is a no-op on
            # non-Windows platforms and on Windows versions before Windows 11.
            QtCore.QTimer.singleShot(0, lambda: apply_windows_11_shell(parent.window()))

    def set_filename(self, filename: str | None) -> None:
        self.file_label.setText(filename or "No source loaded")
        self.file_label.setToolTip(filename or "")

    def set_status(self, prepared: bool, reconstructed: bool, analyzed: bool) -> None:
        """Compatibility no-op: persistent stage status is not header content."""

    def set_action_availability(
        self,
        source_available: bool,
        prepared_available: bool,
        raw_available: bool,
        processed_available: bool,
    ) -> None:
        """Keep global actions aligned with the currently reproducible workspace state."""

        # Actions live with the scientific stage which produces their result.
        del source_available, prepared_available, raw_available, processed_available
