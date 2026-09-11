"""Integration-safe coordinator for the staged Map Reconstruction workspace.

The pre-three-stage composition root is retained in ``_main_window_base`` so
this module can concentrate the cross-stage state contracts introduced by
Signal Preparation without duplicating the mature reconstruction UI code.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PySide6 import QtCore, QtWidgets  # type: ignore[import-not-found]

from map_reconstruction.display_units import display_unit_for_signal
from map_reconstruction.importers.happymeasure import import_happymeasure_csv_bytes
from map_reconstruction.methods.dual_offset import reconstruct_map
from map_reconstruction.models import TimeSeriesData
from map_reconstruction.preparation import SignalPreparationConfig, prepare_signal
from map_reconstruction.project_io import load_project
from map_reconstruction.processing import MapProcessingConfig
from map_reconstruction.ui._main_window_base import (
    MAX_GUIDES_PER_FAMILY,
    MapReconstructionWindow as _BaseWindow,
)
from map_reconstruction.ui.exporting import (
    export_both,
    export_parameter_summary,
    export_html_report,
    export_prepared,
    export_raw,
)
from map_reconstruction.ui.map_views import MapViews


class MapReconstructionWindow(_BaseWindow):
    """Repair cross-stage state ownership while preserving the established UI."""

    def __init__(self, initial_path: Path | None = None) -> None:
        # Let the base class construct the established workspace, but defer any
        # requested initial load until this subclass is fully initialized.
        super().__init__(None)
        self._preparation_error: str | None = None
        header = self.workflow_header
        header.exportPreparedRequested.connect(lambda: export_prepared(self))
        header.exportRawRequested.connect(lambda: export_raw(self))
        header.exportBothRequested.connect(lambda: export_both(self))
        header.exportSummaryRequested.connect(lambda: export_parameter_summary(self))
        header.exportPdfRequested.connect(lambda: export_html_report(self))
        if initial_path is not None:
            self.load_file(initial_path)

    def _sync_preparation_controls(self, config: SignalPreparationConfig) -> None:
        page = self.preparation_page
        if self.data is not None:
            signal = page.signal_combo.currentText() or self.signal_combo.currentText()
            if signal in self.data.signals:
                page.set_display_unit(display_unit_for_signal(signal, self.data.signals[signal]))
        page.set_configuration(config)

    def _show_prepared_diagnostics(self) -> None:
        if self.prepared is None:
            self.preparation_page.set_diagnostics(
                self._preparation_error or "Signal preparation is unavailable."
            )
            return
        baseline_text = (
            "none"
            if self.prepared.baseline is None
            else f"{self.prepared.baseline[0]:.6g} → {self.prepared.baseline[-1]:.6g} SI"
        )
        detail = (
            "; ".join(self.prepared.warnings)
            if self.prepared.warnings
            else "Prepared signal ready."
        )
        self.preparation_page.set_diagnostics(
            f"Samples: {self.prepared.sample_count}\nBaseline: {baseline_text}\n{detail}"
        )

    def _invalidate_preparation(self, message: str) -> None:
        self._preparation_error = message
        self.prepared = None
        self.preparation_page.set_prepared(None)
        self.trace_view.set_prepared_signal(None)
        self.preparation_page.set_diagnostics(message)
        self._invalidate_reconstruction(
            "Reconstruction unavailable — fix Signal Preparation.",
            analysis_message="No processed map available.",
        )
        self.workflow_header.set_status(False, False, False)

    def _preparation_changed(self) -> None:
        if self._restoring_project or self.data is None:
            return
        try:
            config = self.preparation_page.configuration()
        except ValueError as exc:
            self._invalidate_preparation(str(exc))
            return
        # The current widget snapshot becomes authoritative even when the
        # scientific pipeline rejects it (for example, too few manual regions).
        self.preparation_config = config
        try:
            prepared = prepare_signal(self.data, self.signal_combo.currentText(), config)
        except ValueError as exc:
            self._invalidate_preparation(str(exc))
            return
        self._preparation_error = None
        self.prepared = prepared
        self.preparation_page.set_prepared(prepared)
        self.trace_view.set_prepared_signal(prepared.values)
        self._show_prepared_diagnostics()
        self._reconstruct()

    def load_project_file(self, path: Path) -> None:
        try:
            loaded = load_project(path)
            data = import_happymeasure_csv_bytes(
                loaded.raw_csv_bytes,
                loaded.state.original_filename,
                source_path=Path(loaded.state.original_filename),
            )
            if loaded.state.signal not in data.signals:
                raise ValueError(f"Project source signal {loaded.state.signal!r} is unavailable.")
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            QtWidgets.QMessageBox.critical(self, "Could not open project", str(exc))
            return
        if not self._confirm_workspace_replacement():
            return

        preparation_error: str | None = None
        self._restoring_project = True
        try:
            self._load_data(
                data, loaded.raw_csv_bytes, loaded.state.original_filename, reconstruct=False
            )
            project_unit = display_unit_for_signal(
                loaded.state.signal, data.signals[loaded.state.signal]
            )
            self.inspector.restore_project_state(loaded.state, project_unit.scale)
            self.analysis_page.set_processing_config(loaded.state.processing, project_unit.scale)
            blockers = [
                QtCore.QSignalBlocker(self.analysis_page.flip_y_check),
                QtCore.QSignalBlocker(self.preparation_page.signal_combo),
            ]
            try:
                self.analysis_page.flip_y_check.setChecked(loaded.state.flip_y)
                self.preparation_page.signal_combo.setCurrentText(loaded.state.signal)
            finally:
                del blockers
            self.preparation_config = loaded.state.preparation
            self.preparation_page.set_display_unit(project_unit)
            self.preparation_page.set_source(data.time_s, data.signals[loaded.state.signal])
            self._sync_preparation_controls(self.preparation_config)
            try:
                self.prepared = prepare_signal(data, loaded.state.signal, self.preparation_config)
            except ValueError as exc:
                preparation_error = str(exc)
                self._preparation_error = preparation_error
                self.prepared = None
                self.preparation_page.set_prepared(None)
                self.trace_view.set_prepared_signal(None)
            else:
                self._preparation_error = None
                self.preparation_page.set_prepared(self.prepared)
                self.trace_view.set_prepared_signal(self.prepared.values)
            self._set_raw_signal(loaded.state.signal)
            self._update_processing_units()
            self._create_anchor_lines()
            self._show_prepared_diagnostics()
        finally:
            self._restoring_project = False

        if preparation_error is not None:
            self._invalidate_reconstruction(
                "Reconstruction unavailable — fix Signal Preparation.",
                analysis_message="No processed map available.",
            )
            self.preparation_page.set_diagnostics(
                "Project state restored. Fix Signal Preparation before reconstruction.\n"
                + preparation_error
            )
            self._select_stage(0)
            return
        if loaded.state.is_geometry_set:
            self._reconstruct()
            self._select_stage(1)
        else:
            self._set_export_availability()
            self.statusBar().showMessage("Project opened. Set Rows and Columns to reconstruct.")
            self._select_stage(0)

    def _load_data(
        self,
        data: TimeSeriesData,
        raw_bytes: bytes,
        original_filename: str,
        *,
        reconstruct: bool = True,
    ) -> None:
        # Perform the base reset atomically with preparation callbacks suppressed.
        old_restoring = self._restoring_project
        self._restoring_project = True
        try:
            super()._load_data(data, raw_bytes, original_filename, reconstruct=False)
        finally:
            self._restoring_project = old_restoring
        preferred = "Current_A" if "Current_A" in data.signals else data.signal_names[-1]
        self._preparation_error = None
        unit = display_unit_for_signal(preferred, data.signals[preferred])
        self.analysis_page.set_processing_config(MapProcessingConfig(), unit.scale)
        self.preparation_page.set_display_unit(unit)
        self.preparation_page.set_source(data.time_s, data.signals[preferred])
        self.preparation_config = SignalPreparationConfig()
        self._sync_preparation_controls(self.preparation_config)
        self.prepared = prepare_signal(data, preferred, self.preparation_config)
        self.preparation_page.set_prepared(self.prepared)
        self.trace_view.set_prepared_signal(self.prepared.values)
        self._show_prepared_diagnostics()
        self.workflow_header.set_status(True, False, False)
        self._set_export_availability()
        if reconstruct:
            self._reconstruct()
        if reconstruct and (self.rows_spin.value() <= 0 or self.cols_spin.value() <= 0):
            self.statusBar().showMessage("Set Rows and Columns to reconstruct.")

    def _signal_changed(self, signal_name: str) -> None:
        if self.data is None or signal_name not in self.data.signals:
            return
        for combo in (self.inspector.signal_combo, self.preparation_page.signal_combo):
            if combo.currentText() != signal_name:
                blocker = QtCore.QSignalBlocker(combo)
                combo.setCurrentText(signal_name)
                del blocker
        unit = display_unit_for_signal(signal_name, self.data.signals[signal_name])
        self.preparation_page.set_display_unit(unit)
        self.preparation_page.set_source(self.data.time_s, self.data.signals[signal_name])
        # Re-render the same scientific config in the new signal's display units.
        self.preparation_page.set_configuration(self.preparation_config)
        try:
            self.prepared = prepare_signal(self.data, signal_name, self.preparation_config)
        except ValueError as exc:
            self._set_raw_signal(signal_name)
            self._update_processing_units()
            self._invalidate_preparation(str(exc))
            return
        self._preparation_error = None
        self.preparation_page.set_prepared(self.prepared)
        self.trace_view.set_prepared_signal(self.prepared.values)
        self._show_prepared_diagnostics()
        self._set_raw_signal(signal_name)
        self._update_processing_units()
        self._reconstruct()

    def _set_export_availability(self) -> None:
        super()._set_export_availability()
        raw_available = self.result is not None
        processed_available = bool(
            self.processed is not None and np.isfinite(self.processed.values).any()
        )
        source_available = self.data is not None and bool(self._raw_source_bytes)
        self.workflow_header.set_action_availability(
            source_available, self.prepared is not None, raw_available, processed_available
        )
        self.preparation_page.export_button.setEnabled(self.prepared is not None)

    @staticmethod
    def _copy_distribution_controls(source: MapViews, target: MapViews) -> None:
        widgets = (
            target.distribution_range_combo,
            target.distribution_bin_combo,
            target.distribution_min_spin,
            target.distribution_max_spin,
            target.distribution_count_spin,
            target.distribution_width_spin,
        )
        blockers = [QtCore.QSignalBlocker(widget) for widget in widgets]
        try:
            target.distribution_range_combo.setCurrentIndex(
                target.distribution_range_combo.findData(
                    source.distribution_range_combo.currentData()
                )
            )
            target.distribution_bin_combo.setCurrentIndex(
                target.distribution_bin_combo.findData(source.distribution_bin_combo.currentData())
            )
            target.distribution_min_spin.setValue(source.distribution_min_spin.value())
            target.distribution_max_spin.setValue(source.distribution_max_spin.value())
            target.distribution_count_spin.setValue(source.distribution_count_spin.value())
            target.distribution_width_spin.setValue(source.distribution_width_spin.value())
            target._update_distribution_control_visibility()
        finally:
            del blockers

    def _distribution_controls_changed(self) -> None:
        sender = self.sender()
        source = sender if isinstance(sender, MapViews) else self.map_views
        target = self.analysis_map_views if source is self.map_views else self.map_views
        self._copy_distribution_controls(source, target)
        if self.processed is not None:
            self._update_distribution(source)

    def _use_map_limits_for_distribution(self) -> None:
        if self._active_color_limits is None:
            for views in (self.map_views, self.analysis_map_views):
                views.show_distribution_error("Map color limits are not available.")
            return
        sender = self.sender()
        source = sender if isinstance(sender, MapViews) else self.map_views
        source.set_manual_distribution_range(*self._active_color_limits)

    def _update_distribution(self, source: MapViews | None = None) -> None:
        if self.processed is None:
            return
        source = source or self.map_views
        display_unit = self._current_display_unit()
        try:
            config = source.histogram_config(display_unit.scale)
            self.map_views.show_distribution(self.processed, display_unit, config)
            self.analysis_map_views.show_distribution(self.processed, display_unit, config)
        except ValueError as exc:
            self.map_views.show_distribution_error(str(exc))
            self.analysis_map_views.show_distribution_error(str(exc))

    def _convert_legacy_to_phase_window(self) -> None:
        if self.prepared is None:
            message = (
                self._preparation_error or "Fix Signal Preparation before converting registration."
            )
            self.inspector.set_warning(message)
            self.statusBar().showMessage(message)
            return
        super()._convert_legacy_to_phase_window()

    def _reconstruct(self) -> None:
        if self.data is None or self._syncing or self._restoring_project:
            return
        if self.prepared is None:
            # Loaded workspaces never revive an older config after preparation
            # validation failed. Preserve only the historical direct-injection
            # test path where no source archive exists and preparation is identity.
            if (
                self._raw_source_bytes is None
                and self._preparation_error is None
                and self.preparation_config.is_identity
            ):
                try:
                    self.prepared = prepare_signal(
                        self.data, self.signal_combo.currentText(), self.preparation_config
                    )
                except ValueError:
                    self._invalidate_reconstruction(
                        "Reconstruction unavailable — fix Signal Preparation.",
                        analysis_message="No processed map available.",
                    )
                    return
            else:
                self._invalidate_reconstruction(
                    "Reconstruction unavailable — fix Signal Preparation.",
                    analysis_message="No processed map available.",
                )
                return
        super()._reconstruct()

    def _project_state(self):
        # Serialize the visible widget snapshot rather than a potentially stale
        # previously-valid config. This also permits repairable draft projects.
        self.preparation_config = self.preparation_page.configuration()
        return super()._project_state()


def run_app(path: Path | None = None) -> int:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    window = MapReconstructionWindow(path)
    window.showMaximized()
    return app.exec()


__all__ = ["MAX_GUIDES_PER_FAMILY", "MapReconstructionWindow", "reconstruct_map", "run_app"]
