"""SQLite-backed persistent dataset store.

This module extends the in-memory DatasetStore with SQLite persistence,
providing:
- Automatic save/load of measurement traces
- Session management (save/restore UI state)
- Query and filtering capabilities
- Backup and recovery
- Efficient storage of large datasets
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from keith_ivt.data.dataset_store import DatasetStore, DeviceTrace
from keith_ivt.models import SweepConfig, SweepMode, SweepPoint, SweepResult, Terminal, SenseMode, SweepKind

logger = logging.getLogger("keith_ivt.data.persistent_store")

# Database schema version
DB_VERSION = 1


class PersistentDatasetStore(DatasetStore):
    """SQLite-backed trace store with automatic persistence.

    Extends the in-memory DatasetStore with database persistence.
    All operations are automatically saved to disk.

    Usage:
        >>> store = PersistentDatasetStore("data/happymeasure.db")
        >>> store.add_result(sweep_result, "MyMeasurement")
        >>> # Data is automatically saved
        >>> # Later...
        >>> store2 = PersistentDatasetStore("data/happymeasure.db")
        >>> # Previous data is loaded automatically
    """

    def __init__(self, db_path: str | Path = "data/happymeasure.db", auto_load: bool = True):
        """Initialize persistent store.

        Args:
            db_path: Path to SQLite database file
            auto_load: Whether to load existing data on initialization
        """
        super().__init__()
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._session_id: str | None = None

        # Initialize database
        self._init_database()

        # Load existing data if requested
        if auto_load:
            self._load_from_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self) -> None:
        """Create database tables if they don't exist."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Create schema version table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            # Store/check schema version
            cursor.execute("SELECT value FROM metadata WHERE key = 'schema_version'")
            row = cursor.fetchone()
            if row is None:
                cursor.execute(
                    "INSERT INTO metadata (key, value) VALUES ('schema_version', ?)",
                    (str(DB_VERSION),)
                )
            else:
                version = int(row["value"])
                if version != DB_VERSION:
                    logger.warning(f"Schema version mismatch: {version} vs {DB_VERSION}")

            # Create traces table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS traces (
                    trace_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    color TEXT NOT NULL DEFAULT '#1f77b4',
                    visible INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP NOT NULL,
                    config_json TEXT NOT NULL,
                    session_id TEXT
                )
            """)

            # Create points table (normalized for efficiency)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sweep_points (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trace_id INTEGER NOT NULL,
                    point_index INTEGER NOT NULL,
                    source_value REAL NOT NULL,
                    measured_value REAL NOT NULL,
                    elapsed_s REAL NOT NULL DEFAULT 0.0,
                    timestamp TEXT,
                    FOREIGN KEY (trace_id) REFERENCES traces(trace_id) ON DELETE CASCADE
                )
            """)

            # Create index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_points_trace_id
                ON sweep_points(trace_id)
            """)

            # Create sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TIMESTAMP NOT NULL,
                    metadata_json TEXT
                )
            """)

            conn.commit()
            logger.info(f"Database initialized: {self.db_path}")

        finally:
            conn.close()

    def _load_from_database(self) -> None:
        """Load all traces from database into memory."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Load traces
            cursor.execute("SELECT * FROM traces ORDER BY created_at")
            trace_rows = cursor.fetchall()

            for trace_row in trace_rows:
                # Parse config
                config_data = json.loads(trace_row["config_json"])
                config = self._dict_to_config(config_data)

                # Load points
                cursor.execute(
                    "SELECT * FROM sweep_points WHERE trace_id = ? ORDER BY point_index",
                    (trace_row["trace_id"],)
                )
                point_rows = cursor.fetchall()

                points = [
                    SweepPoint(
                        source_value=row["source_value"],
                        measured_value=row["measured_value"],
                        elapsed_s=row["elapsed_s"],
                        timestamp=row["timestamp"] or "",
                    )
                    for row in point_rows
                ]

                # Create result
                result = SweepResult(config=config, points=points)

                # Create trace
                trace = DeviceTrace(
                    result=result,
                    name=trace_row["name"],
                    trace_id=trace_row["trace_id"],
                    visible=bool(trace_row["visible"]),
                    color=trace_row["color"],
                    created_at=datetime.fromisoformat(trace_row["created_at"]),
                )

                self._traces.append(trace)

            logger.info(f"Loaded {len(self._traces)} traces from database")

        finally:
            conn.close()

    def add_result(self, result: SweepResult, name: str | None = None) -> DeviceTrace:
        """Add a sweep result and persist to database.

        Args:
            result: Sweep result to add
            name: Optional custom name

        Returns:
            Created DeviceTrace
        """
        # Add to in-memory store
        trace = super().add_result(result, name)

        # Persist to database
        self._save_trace_to_db(trace)

        return trace

    def _save_trace_to_db(self, trace: DeviceTrace) -> None:
        """Save a single trace to database."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Serialize config
            config_json = json.dumps(self._config_to_dict(trace.result.config))

            # Insert trace
            cursor.execute("""
                INSERT INTO traces (trace_id, name, color, visible, created_at, config_json, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                trace.trace_id,
                trace.name,
                trace.color,
                int(trace.visible),
                trace.created_at.isoformat(),
                config_json,
                self._session_id,
            ))

            # Insert points
            for idx, point in enumerate(trace.result.points):
                cursor.execute("""
                    INSERT INTO sweep_points
                    (trace_id, point_index, source_value, measured_value, elapsed_s, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    trace.trace_id,
                    idx,
                    point.source_value,
                    point.measured_value,
                    point.elapsed_s,
                    point.timestamp if point.timestamp else None,
                ))

            conn.commit()
            logger.debug(f"Saved trace {trace.trace_id} ({trace.name}) to database")

        finally:
            conn.close()

    def remove(self, trace_id: int) -> None:
        """Remove trace from memory and database."""
        # Remove from memory
        super().remove(trace_id)

        # Remove from database
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM traces WHERE trace_id = ?", (trace_id,))
            # Points are deleted via CASCADE
            conn.commit()
            logger.debug(f"Removed trace {trace_id} from database")
        finally:
            conn.close()

    def clear(self) -> None:
        """Clear all traces from memory and database."""
        # Clear memory
        super().clear()

        # Clear database
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM traces")
            cursor.execute("DELETE FROM sweep_points")
            conn.commit()
            logger.info("Cleared all traces from database")
        finally:
            conn.close()

    def rename(self, trace_id: int, new_name: str) -> None:
        """Rename trace and update database."""
        # Update memory
        super().rename(trace_id, new_name)

        # Update database
        trace = self.get(trace_id)
        if trace:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE traces SET name = ? WHERE trace_id = ?",
                    (trace.name, trace_id)
                )
                conn.commit()
            finally:
                conn.close()

    def toggle_visibility(self, trace_id: int) -> None:
        """Toggle visibility and update database."""
        # Update memory
        super().toggle_visibility(trace_id)

        # Update database
        trace = self.get(trace_id)
        if trace:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE traces SET visible = ? WHERE trace_id = ?",
                    (int(trace.visible), trace_id)
                )
                conn.commit()
            finally:
                conn.close()

    def set_color(self, trace_id: int, color: str) -> None:
        """Set trace color and update database."""
        # Update memory
        super().set_color(trace_id, color)

        # Update database
        trace = self.get(trace_id)
        if trace:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE traces SET color = ? WHERE trace_id = ?",
                    (color, trace_id)
                )
                conn.commit()
            finally:
                conn.close()

    # ========================================================================
    # Session Management
    # ========================================================================

    def start_session(self, session_id: str | None = None, metadata: dict[str, Any] | None = None) -> str:
        """Start a new measurement session.

        Args:
            session_id: Custom session ID (generated if None)
            metadata: Optional session metadata

        Returns:
            Session ID
        """
        import uuid

        if session_id is None:
            session_id = str(uuid.uuid4())

        self._session_id = session_id

        # Save session record
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO sessions (session_id, created_at, metadata_json)
                VALUES (?, ?, ?)
            """, (
                session_id,
                datetime.now().isoformat(),
                json.dumps(metadata or {}),
            ))
            conn.commit()
            logger.info(f"Started session: {session_id}")
        finally:
            conn.close()

        return session_id

    def get_session_metadata(self, session_id: str) -> dict[str, Any]:
        """Retrieve metadata for a session.

        Args:
            session_id: Session ID

        Returns:
            Session metadata dictionary
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT metadata_json FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            if row:
                return json.loads(row["metadata_json"])
            return {}
        finally:
            conn.close()

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all stored sessions.

        Returns:
            List of session info dictionaries
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions ORDER BY created_at DESC")
            rows = cursor.fetchall()

            return [
                {
                    "session_id": row["session_id"],
                    "created_at": row["created_at"],
                    "metadata": json.loads(row["metadata_json"]),
                }
                for row in rows
            ]
        finally:
            conn.close()

    # ========================================================================
    # Query and Export
    # ========================================================================

    def query_traces(
        self,
        name_pattern: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        visible_only: bool = False,
    ) -> list[DeviceTrace]:
        """Query traces with filters.

        Args:
            name_pattern: SQL LIKE pattern for name matching (e.g., "%Device%")
            date_from: Filter traces created after this date
            date_to: Filter traces created before this date
            visible_only: Only return visible traces

        Returns:
            Matching traces (in-memory only, not re-loaded from DB)
        """
        traces = self.all()

        if name_pattern:
            traces = [t for t in traces if name_pattern.lower() in t.name.lower()]

        if date_from:
            traces = [t for t in traces if t.created_at >= date_from]

        if date_to:
            traces = [t for t in traces if t.created_at <= date_to]

        if visible_only:
            traces = [t for t in traces if t.visible]

        return traces

    def get_trace_count(self) -> int:
        """Get total number of traces in database."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM traces")
            row = cursor.fetchone()
            return row["count"] if row else 0
        finally:
            conn.close()

    def get_database_size(self) -> int:
        """Get database file size in bytes."""
        if self.db_path.exists():
            return self.db_path.stat().st_size
        return 0

    def backup_database(self, backup_path: str | Path | None = None) -> Path:
        """Create a backup of the database.

        Args:
            backup_path: Custom backup path (auto-generated if None)

        Returns:
            Path to backup file
        """
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.db_path.with_suffix(f".{timestamp}.bak")
        else:
            backup_path = Path(backup_path)

        conn = self._get_connection()
        try:
            # Use SQLite's backup API for consistency
            backup_conn = sqlite3.connect(str(backup_path))
            try:
                conn.backup(backup_conn)
                logger.info(f"Database backed up to: {backup_path}")
            finally:
                backup_conn.close()
        finally:
            conn.close()

        return Path(backup_path)

    def vacuum(self) -> None:
        """Reclaim unused database space."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("VACUUM")
            conn.commit()
            logger.info("Database vacuumed")
        finally:
            conn.close()

    # ========================================================================
    # Helper Methods
    # ========================================================================

    @staticmethod
    def _config_to_dict(config: SweepConfig) -> dict[str, Any]:
        """Convert SweepConfig to JSON-serializable dict."""
        return {
            "mode": config.mode.value,
            "start": config.start,
            "stop": config.stop,
            "step": config.step,
            "compliance": config.compliance,
            "nplc": config.nplc,
            "terminal": config.terminal.value,
            "sense_mode": config.sense_mode.value,
            "device_name": config.device_name,
            "operator": config.operator,
            "debug": config.debug,
            "output_off_after_run": config.output_off_after_run,
            "sweep_kind": config.sweep_kind.value,
            "constant_value": config.constant_value,
            "duration_s": config.duration_s,
            "continuous_time": config.continuous_time,
            "interval_s": config.interval_s,
            "autorange": config.autorange,
            "auto_source_range": config.auto_source_range,
            "auto_measure_range": config.auto_measure_range,
            "source_range": config.source_range,
            "measure_range": config.measure_range,
            "adaptive_logic": config.adaptive_logic,
            "debug_model": config.debug_model,
        }

    @staticmethod
    def _dict_to_config(data: dict[str, Any]) -> SweepConfig:
        """Convert dict back to SweepConfig."""
        return SweepConfig(
            mode=SweepMode(data["mode"]),
            start=data["start"],
            stop=data["stop"],
            step=data["step"],
            compliance=data["compliance"],
            nplc=data["nplc"],
            terminal=Terminal(data["terminal"]),
            sense_mode=SenseMode(data["sense_mode"]),
            device_name=data.get("device_name", ""),
            operator=data.get("operator", ""),
            debug=data.get("debug", False),
            output_off_after_run=data.get("output_off_after_run", True),
            sweep_kind=SweepKind(data.get("sweep_kind", "STEP")),
            constant_value=data.get("constant_value", 0.0),
            duration_s=data.get("duration_s", 10.0),
            continuous_time=data.get("continuous_time", False),
            interval_s=data.get("interval_s", 0.5),
            autorange=data.get("autorange", True),
            auto_source_range=data.get("auto_source_range", True),
            auto_measure_range=data.get("auto_measure_range", True),
            source_range=data.get("source_range", 0.0),
            measure_range=data.get("measure_range", 0.0),
            adaptive_logic=data.get("adaptive_logic", ""),
            debug_model=data.get("debug_model", ""),
        )


# Convenience function for easy import
def create_persistent_store(db_path: str | Path = "data/happymeasure.db") -> PersistentDatasetStore:
    """Create a persistent dataset store.

    Args:
        db_path: Path to SQLite database

    Returns:
        Initialized PersistentDatasetStore
    """
    return PersistentDatasetStore(db_path=db_path)
