"""Headless, self-contained persistence for Map Reconstruction projects."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import os
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from map_reconstruction.models import (
    Aggregation,
    DualOffsetParams,
    PhaseWindowParams,
    ScanPattern,
    WindowMode,
)
from map_reconstruction.processing import (
    BaselineMode,
    ColorRangeMode,
    MapProcessingConfig,
    NormalizationMode,
    ValueScale,
    ValueTransform,
)
from map_reconstruction.preparation import SignalPreparationConfig

PROJECT_SCHEMA = "map-reconstruction-project-v1"
PROJECT_SCHEMA_V2 = "map-reconstruction-project-v2"
PROJECT_SCHEMA_V3 = "map-reconstruction-project-v3"
PROJECT_JSON_PATH = "project.json"
RAW_CSV_PATH = "source/raw_timeseries.csv"


def _finite_float(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Invalid project field {name}: expected a number.")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"Invalid project field {name}: expected a finite number.")
    return result


def _integer(value: object, name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"Invalid project field {name}: expected an integer >= {minimum}.")
    return value


def _boolean(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"Invalid project field {name}: expected true or false.")
    return value


def _string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Invalid project field {name}: expected a non-empty string.")
    return value


def _filename(value: object) -> str:
    filename = _string(value, "source.original_filename")
    if Path(filename).name != filename or "/" in filename or "\\" in filename:
        raise ValueError(
            "Invalid project field source.original_filename: expected a filename only."
        )
    return filename


def _mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Invalid project field {name}: expected an object.")
    return value


@dataclass(frozen=True, slots=True)
class ProjectState:
    """Scientific workspace state stored in a ``.hmmap`` archive.

    Raw CSV bytes are deliberately not part of this model. They are kept as a
    separate archive member so that their exact source representation can be
    hashed and preserved byte-for-byte.
    """

    original_filename: str
    signal: str
    rows: int
    columns: int
    scan_pattern: ScanPattern
    first_row_ltr: bool
    aggregation: str
    row_a_s: float
    row_b_s: float
    rows_apart: int
    row_offset: int
    point_a_s: float
    point_b_s: float
    points_apart: int
    point_offset: int
    processing: MapProcessingConfig
    flip_y: bool
    method: str = "dual_offset"
    y_phase_fraction: float = 0.0
    x_period_offset: int = 0
    x_phase_fraction: float = 0.0
    window_mode: WindowMode = WindowMode.FRACTION
    window_fraction: float = 0.65
    window_duration_s: float | None = None
    preparation: SignalPreparationConfig = SignalPreparationConfig()

    def __post_init__(self) -> None:
        object.__setattr__(self, "original_filename", _filename(self.original_filename))
        object.__setattr__(self, "signal", _string(self.signal, "source.signal"))
        object.__setattr__(self, "rows", _integer(self.rows, "geometry.rows"))
        object.__setattr__(self, "columns", _integer(self.columns, "geometry.columns"))
        object.__setattr__(self, "scan_pattern", ScanPattern(self.scan_pattern))
        object.__setattr__(
            self, "first_row_ltr", _boolean(self.first_row_ltr, "geometry.first_row_ltr")
        )
        if self.aggregation not in ("median", "mean"):
            raise ValueError("Invalid project field geometry.aggregation.")
        object.__setattr__(self, "row_a_s", _finite_float(self.row_a_s, "registration.row_a_s"))
        object.__setattr__(self, "row_b_s", _finite_float(self.row_b_s, "registration.row_b_s"))
        object.__setattr__(
            self, "point_a_s", _finite_float(self.point_a_s, "registration.point_a_s")
        )
        object.__setattr__(
            self, "point_b_s", _finite_float(self.point_b_s, "registration.point_b_s")
        )
        object.__setattr__(
            self, "rows_apart", _integer(self.rows_apart, "registration.rows_apart", minimum=1)
        )
        object.__setattr__(
            self,
            "points_apart",
            _integer(self.points_apart, "registration.points_apart", minimum=1),
        )
        object.__setattr__(self, "row_offset", _integer(self.row_offset, "registration.row_offset"))
        object.__setattr__(
            self, "point_offset", _integer(self.point_offset, "registration.point_offset")
        )
        object.__setattr__(self, "flip_y", _boolean(self.flip_y, "display.flip_y"))
        if self.method not in ("dual_offset", "dual_offset_phase_window"):
            raise ValueError("Unsupported Map Reconstruction registration method.")
        object.__setattr__(
            self,
            "y_phase_fraction",
            _finite_float(self.y_phase_fraction, "registration.y_phase_fraction") % 1.0,
        )
        object.__setattr__(
            self,
            "x_phase_fraction",
            _finite_float(self.x_phase_fraction, "registration.x_phase_fraction") % 1.0,
        )
        object.__setattr__(
            self, "x_period_offset", _integer(self.x_period_offset, "registration.x_period_offset")
        )
        object.__setattr__(self, "window_mode", WindowMode(self.window_mode))
        if self.window_duration_s is not None:
            object.__setattr__(
                self,
                "window_duration_s",
                _finite_float(self.window_duration_s, "registration.window_duration_s"),
            )
        object.__setattr__(
            self,
            "window_fraction",
            _finite_float(self.window_fraction, "registration.window_fraction"),
        )
        if not isinstance(self.processing, MapProcessingConfig):
            raise ValueError("Invalid project field processing.")
        if not isinstance(self.preparation, SignalPreparationConfig):
            raise ValueError("Invalid project field preparation.")
        if bool(self.rows) != bool(self.columns):
            raise ValueError(
                "Invalid project geometry: rows and columns must both be set or both be zero."
            )
        if self.rows:
            if self.method == "dual_offset":
                DualOffsetParams(
                    rows=self.rows,
                    cols=self.columns,
                    row_a_s=self.row_a_s,
                    row_b_s=self.row_b_s,
                    rows_apart=self.rows_apart,
                    row_offset=self.row_offset,
                    point_a_s=self.point_a_s,
                    point_b_s=self.point_b_s,
                    points_apart=self.points_apart,
                    point_offset=self.point_offset,
                    scan_pattern=self.scan_pattern,
                    first_row_ltr=self.first_row_ltr,
                    use_median=self.aggregation == "median",
                )
            else:
                PhaseWindowParams(
                    rows=self.rows,
                    cols=self.columns,
                    row_a_s=self.row_a_s,
                    row_b_s=self.row_b_s,
                    rows_apart=self.rows_apart,
                    row_offset=self.row_offset,
                    y_phase_fraction=self.y_phase_fraction,
                    point_a_s=self.point_a_s,
                    point_b_s=self.point_b_s,
                    points_apart=self.points_apart,
                    x_period_offset=self.x_period_offset,
                    x_phase_fraction=self.x_phase_fraction,
                    window_mode=self.window_mode,
                    window_fraction=self.window_fraction,
                    window_duration_s=self.window_duration_s,
                    scan_pattern=self.scan_pattern,
                    first_row_ltr=self.first_row_ltr,
                    aggregation=Aggregation(self.aggregation),
                )
        elif self.row_offset or self.point_offset:
            raise ValueError("Invalid project offsets for unset geometry.")

    @property
    def is_geometry_set(self) -> bool:
        return bool(self.rows and self.columns)

    def to_project_dict(self, *, raw_sha256: str, application_version: str) -> dict[str, object]:
        processing = {
            key: (value.value if hasattr(value, "value") else value)
            for key, value in asdict(self.processing).items()
        }
        return {
            # Keep the compact v1/v2 representation for identity preparation so
            # old callers retain byte-compatible semantics.  Any active
            # preparation is explicitly represented as project schema v3.
            "schema": (
                PROJECT_SCHEMA_V3
                if not self.preparation.is_identity
                else (
                    PROJECT_SCHEMA_V2
                    if self.method == "dual_offset_phase_window"
                    else PROJECT_SCHEMA
                )
            ),
            "application": {"name": "Map Reconstruction", "version": application_version},
            "created_at": datetime.now(UTC).isoformat(),
            "source": {
                "original_filename": self.original_filename,
                "embedded_path": RAW_CSV_PATH,
                "sha256": raw_sha256,
                "signal": self.signal,
            },
            "geometry": {
                "rows": self.rows,
                "columns": self.columns,
                "scan_pattern": self.scan_pattern.value,
                "first_row_ltr": self.first_row_ltr,
                "aggregation": self.aggregation,
            },
            "registration": {
                "method": self.method,
                "row_a_s": self.row_a_s,
                "row_b_s": self.row_b_s,
                "rows_apart": self.rows_apart,
                "row_offset": self.row_offset,
                "point_a_s": self.point_a_s,
                "point_b_s": self.point_b_s,
                "points_apart": self.points_apart,
                **(
                    {
                        "y_phase_fraction": self.y_phase_fraction,
                        "x_period_offset": self.x_period_offset,
                        "x_phase_fraction": self.x_phase_fraction,
                        "window_mode": self.window_mode.value,
                        "window_fraction": self.window_fraction,
                        "window_duration_s": self.window_duration_s,
                    }
                    if self.method == "dual_offset_phase_window"
                    else {"point_offset": self.point_offset}
                ),
            },
            "processing": processing,
            **({"map_processing": processing} if not self.preparation.is_identity else {}),
            **(
                {"preparation": {"signal": self.signal, **self.preparation.to_dict()}}
                if not self.preparation.is_identity
                else {}
            ),
            "display": {"flip_y": self.flip_y},
        }

    @classmethod
    def from_project_dict(cls, payload: object) -> "ProjectState":
        root = _mapping(payload, "project")
        schema = root.get("schema")
        if not isinstance(schema, str) or schema not in (
            PROJECT_SCHEMA,
            PROJECT_SCHEMA_V2,
            PROJECT_SCHEMA_V3,
        ):
            raise ValueError(f"Unsupported Map Reconstruction project schema: {schema!r}")
        source = _mapping(root.get("source"), "source")
        geometry = _mapping(root.get("geometry"), "geometry")
        registration = _mapping(root.get("registration"), "registration")
        method = registration.get("method")
        if method not in ("dual_offset", "dual_offset_phase_window"):
            raise ValueError("Unsupported Map Reconstruction registration method.")
        if schema == PROJECT_SCHEMA and method != "dual_offset":
            raise ValueError("Version 1 projects must use Legacy Dual Offset.")
        display = _mapping(root.get("display"), "display")
        processing_payload = root.get("map_processing", root.get("processing"))
        processing = _processing_from_dict(_mapping(processing_payload, "processing"))
        preparation_payload = root.get("preparation")
        if schema == PROJECT_SCHEMA_V3:
            preparation_root = _mapping(preparation_payload, "preparation")
            saved_signal = _string(
                preparation_root.get("signal", source.get("signal")), "preparation.signal"
            )
            if saved_signal != source.get("signal"):
                raise ValueError("Project preparation signal must match source.signal.")
            preparation = SignalPreparationConfig.from_dict(preparation_root)
        else:
            preparation = SignalPreparationConfig()
        try:
            scan_pattern = ScanPattern(geometry.get("scan_pattern"))
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid project field geometry.scan_pattern.") from exc
        return cls(
            original_filename=_filename(source.get("original_filename")),
            signal=_string(source.get("signal"), "source.signal"),
            rows=_integer(geometry.get("rows"), "geometry.rows"),
            columns=_integer(geometry.get("columns"), "geometry.columns"),
            scan_pattern=scan_pattern,
            first_row_ltr=_boolean(geometry.get("first_row_ltr"), "geometry.first_row_ltr"),
            aggregation=_string(geometry.get("aggregation"), "geometry.aggregation"),
            row_a_s=_finite_float(registration.get("row_a_s"), "registration.row_a_s"),
            row_b_s=_finite_float(registration.get("row_b_s"), "registration.row_b_s"),
            rows_apart=_integer(
                registration.get("rows_apart"), "registration.rows_apart", minimum=1
            ),
            row_offset=_integer(registration.get("row_offset"), "registration.row_offset"),
            point_a_s=_finite_float(registration.get("point_a_s"), "registration.point_a_s"),
            point_b_s=_finite_float(registration.get("point_b_s"), "registration.point_b_s"),
            points_apart=_integer(
                registration.get("points_apart"), "registration.points_apart", minimum=1
            ),
            point_offset=_integer(registration.get("point_offset", 0), "registration.point_offset"),
            processing=processing,
            flip_y=_boolean(display.get("flip_y"), "display.flip_y"),
            method=method,
            y_phase_fraction=(
                _finite_float(registration.get("y_phase_fraction"), "registration.y_phase_fraction")
                if method == "dual_offset_phase_window"
                else 0.0
            ),
            x_period_offset=(
                _integer(registration.get("x_period_offset"), "registration.x_period_offset")
                if method == "dual_offset_phase_window"
                else 0
            ),
            x_phase_fraction=(
                _finite_float(registration.get("x_phase_fraction"), "registration.x_phase_fraction")
                if method == "dual_offset_phase_window"
                else 0.0
            ),
            window_mode=(
                WindowMode(registration.get("window_mode"))
                if method == "dual_offset_phase_window"
                else WindowMode.FRACTION
            ),
            window_fraction=(
                _finite_float(registration.get("window_fraction"), "registration.window_fraction")
                if method == "dual_offset_phase_window"
                else 0.65
            ),
            window_duration_s=(
                registration.get("window_duration_s")
                if method == "dual_offset_phase_window"
                else None
            ),
            preparation=preparation,
        )


def _processing_from_dict(payload: dict[str, Any]) -> MapProcessingConfig:
    fields = {
        "baseline_mode",
        "baseline_value",
        "baseline_percentile",
        "transform",
        "custom_expression",
        "normalization",
        "normalization_reference",
        "value_scale",
        "color_range_mode",
        "color_min",
        "color_max",
        "percentile_low",
        "percentile_high",
    }
    missing = fields.difference(payload)
    if missing:
        raise ValueError(f"Invalid project processing: missing {', '.join(sorted(missing))}.")
    optional_numbers = ("baseline_value", "normalization_reference", "color_min", "color_max")
    numeric = ("baseline_percentile", "percentile_low", "percentile_high")
    optional_values: dict[str, float | None] = {}
    numeric_values: dict[str, float] = {}
    for name in optional_numbers:
        raw = payload[name]
        optional_values[name] = None if raw is None else _finite_float(raw, f"processing.{name}")
    for name in numeric:
        numeric_values[name] = _finite_float(payload[name], f"processing.{name}")
    try:
        return MapProcessingConfig(
            baseline_mode=BaselineMode(payload["baseline_mode"]),
            baseline_value=optional_values["baseline_value"],
            baseline_percentile=numeric_values["baseline_percentile"],
            transform=ValueTransform(payload["transform"]),
            custom_expression=_string(payload["custom_expression"], "processing.custom_expression"),
            normalization=NormalizationMode(payload["normalization"]),
            normalization_reference=optional_values["normalization_reference"],
            value_scale=ValueScale(payload["value_scale"]),
            color_range_mode=ColorRangeMode(payload["color_range_mode"]),
            color_min=optional_values["color_min"],
            color_max=optional_values["color_max"],
            percentile_low=numeric_values["percentile_low"],
            percentile_high=numeric_values["percentile_high"],
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid project processing configuration.") from exc


@dataclass(frozen=True, slots=True)
class LoadedProject:
    state: ProjectState
    raw_csv_bytes: bytes
    project_metadata: dict[str, object]


def application_version() -> str:
    """Return installed project version without making development export fragile."""

    try:
        return importlib.metadata.version("HappyMeasure")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def save_project(path: str | Path, state: ProjectState, raw_csv_bytes: bytes) -> None:
    """Write a self-contained archive atomically, preserving source bytes exactly."""

    destination = Path(path)
    if not raw_csv_bytes:
        raise ValueError("Cannot export a project without raw source data.")
    digest = hashlib.sha256(raw_csv_bytes).hexdigest()
    payload = state.to_project_dict(raw_sha256=digest, application_version=application_version())
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{destination.stem}-",
            suffix=".tmp",
            dir=destination.parent,
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
        try:
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(
                    PROJECT_JSON_PATH,
                    json.dumps(payload, indent=2, sort_keys=True, allow_nan=False),
                )
                archive.writestr(RAW_CSV_PATH, raw_csv_bytes)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
    except (OSError, TypeError, ValueError, zipfile.BadZipFile) as exc:
        raise ValueError(f"Could not export Map Reconstruction project: {exc}") from exc


def load_project(path: str | Path) -> LoadedProject:
    """Read and validate known archive members without extracting untrusted ZIP content."""

    try:
        with zipfile.ZipFile(Path(path), "r") as archive:
            names = set(archive.namelist())
            if PROJECT_JSON_PATH not in names:
                raise ValueError("Project archive is missing project.json.")
            if RAW_CSV_PATH not in names:
                raise ValueError("Project archive is missing embedded raw data.")
            project_bytes = archive.read(PROJECT_JSON_PATH)
            raw_csv_bytes = archive.read(RAW_CSV_PATH)
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValueError(f"Could not open Map Reconstruction project: {exc}") from exc
    try:
        payload = json.loads(project_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Project metadata is not valid JSON.") from exc
    root = _mapping(payload, "project")
    source = _mapping(root.get("source"), "source")
    if source.get("embedded_path") != RAW_CSV_PATH:
        raise ValueError("Project embedded raw-data path is invalid.")
    expected_hash = _string(source.get("sha256"), "source.sha256")
    if len(expected_hash) != 64 or any(
        character not in "0123456789abcdef" for character in expected_hash
    ):
        raise ValueError("Invalid project field source.sha256.")
    actual_hash = hashlib.sha256(raw_csv_bytes).hexdigest()
    if actual_hash != expected_hash:
        raise ValueError("Embedded raw data failed SHA-256 verification.")
    state = ProjectState.from_project_dict(root)
    return LoadedProject(state=state, raw_csv_bytes=raw_csv_bytes, project_metadata=root)
