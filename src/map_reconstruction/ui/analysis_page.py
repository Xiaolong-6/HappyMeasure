"""Map Analysis stage shell and display-only controls."""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets  # type: ignore[import-not-found]


class MapAnalysisPage(QtWidgets.QWidget):
    """Dedicated page for post-reconstruction processing and figure state."""

    displayChanged = QtCore.Signal()
    processing_section: QtWidgets.QWidget | None

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("mapAnalysisPage")
        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(14)
        sidebar = QtWidgets.QFrame()
        sidebar.setObjectName("stageSidebar")
        layout = QtWidgets.QVBoxLayout(sidebar)
        self.sidebar_layout = layout
        layout.setContentsMargins(12, 10, 12, 10)
        title = QtWidgets.QLabel("Map Analysis")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        description = QtWidgets.QLabel("Process reconstructed values and control figure display.")
        description.setObjectName("mutedText")
        description.setWordWrap(True)
        layout.addWidget(description)
        self.processing_placeholder = QtWidgets.QLabel(
            "Map value processing controls are active in this stage."
        )
        self.processing_placeholder.setObjectName("analysisControls")
        self.processing_placeholder.setWordWrap(True)
        layout.addWidget(self.processing_placeholder)
        self.palette_combo = QtWidgets.QComboBox()
        self.palette_combo.addItems(
            ("Viridis", "Plasma", "Inferno", "Magma", "Cividis", "Grayscale")
        )
        self.flip_y_check = QtWidgets.QCheckBox("Flip Y display")
        form = QtWidgets.QFormLayout()
        form.addRow("Palette", self.palette_combo)
        layout.addLayout(form)
        layout.addWidget(self.flip_y_check)
        layout.addStretch(1)
        sidebar_scroll = QtWidgets.QScrollArea()
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        sidebar_scroll.setMinimumSize(300, 0)
        sidebar_scroll.setWidget(sidebar)
        root.addWidget(sidebar_scroll, 0)
        self.views_host = QtWidgets.QWidget()
        self.views_layout = QtWidgets.QVBoxLayout(self.views_host)
        self.views_layout.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.views_host, 1)
        self.palette_combo.currentIndexChanged.connect(self.displayChanged)
        self.flip_y_check.toggled.connect(self.displayChanged)
