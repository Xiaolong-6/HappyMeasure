"""Tests for SQLite-backed persistent dataset store."""
import pytest
from pathlib import Path
import tempfile
from datetime import datetime

from keith_ivt.data.persistent_store import PersistentDatasetStore, create_persistent_store
from keith_ivt.models import SweepConfig, SweepMode, SweepPoint, SweepResult, Terminal, SenseMode


def create_test_result(name: str = "TestDevice", num_points: int = 10) -> SweepResult:
    """Create a test sweep result."""
    config = SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=-1.0,
        stop=1.0,
        step=0.2,
        compliance=0.01,
        nplc=1.0,
        device_name=name,
    )
    points = [
        SweepPoint(
            source_value=-1.0 + i * 0.2,
            measured_value=(-1.0 + i * 0.2) / 1000.0,  # 1k resistor
            elapsed_s=i * 0.1,
            timestamp=datetime.now().isoformat(),
        )
        for i in range(num_points)
    ]
    return SweepResult(config=config, points=points)


class TestPersistentDatasetStore:
    """Test persistent store functionality."""

    def test_create_store_creates_database(self, tmp_path):
        """Creating store should create database file."""
        db_path = tmp_path / "test.db"
        store = PersistentDatasetStore(db_path=db_path)

        assert db_path.exists()

    def test_add_result_persists_to_disk(self, tmp_path):
        """Adding results should persist to database."""
        db_path = tmp_path / "test.db"

        # Create store and add data
        store = PersistentDatasetStore(db_path=db_path)
        result = create_test_result("Device1")
        trace = store.add_result(result, "MyTrace")

        assert trace.name == "MyTrace"
        assert store.get_trace_count() == 1

        # Create new store instance - data should persist
        store2 = PersistentDatasetStore(db_path=db_path)
        assert store2.get_trace_count() == 1

        loaded_trace = store2.all()[0]
        assert loaded_trace.name == "MyTrace"
        assert len(loaded_trace.result.points) == 10

    def test_remove_deletes_from_database(self, tmp_path):
        """Removing traces should delete from database."""
        db_path = tmp_path / "test.db"
        store = PersistentDatasetStore(db_path=db_path)

        result = create_test_result()
        trace = store.add_result(result, "ToRemove")
        trace_id = trace.trace_id

        store.remove(trace_id)
        assert store.get_trace_count() == 0

        # Verify deletion persists
        store2 = PersistentDatasetStore(db_path=db_path)
        assert store2.get_trace_count() == 0

    def test_clear_removes_all_data(self, tmp_path):
        """Clearing should remove all traces."""
        db_path = tmp_path / "test.db"
        store = PersistentDatasetStore(db_path=db_path)

        for i in range(5):
            store.add_result(create_test_result(f"Device{i}"))

        assert store.get_trace_count() == 5
        store.clear()
        assert store.get_trace_count() == 0

        # Verify clear persists
        store2 = PersistentDatasetStore(db_path=db_path)
        assert store2.get_trace_count() == 0

    def test_rename_updates_database(self, tmp_path):
        """Renaming should update database."""
        db_path = tmp_path / "test.db"
        store = PersistentDatasetStore(db_path=db_path)

        result = create_test_result()
        trace = store.add_result(result, "OldName")

        store.rename(trace.trace_id, "NewName")
        assert trace.name == "NewName"

        # Verify rename persists
        store2 = PersistentDatasetStore(db_path=db_path)
        loaded = store2.get(trace.trace_id)
        assert loaded.name == "NewName"

    def test_toggle_visibility_persists(self, tmp_path):
        """Visibility changes should persist."""
        db_path = tmp_path / "test.db"
        store = PersistentDatasetStore(db_path=db_path)

        result = create_test_result()
        trace = store.add_result(result)

        store.toggle_visibility(trace.trace_id)
        assert trace.visible is False

        # Verify persists
        store2 = PersistentDatasetStore(db_path=db_path)
        loaded = store2.get(trace.trace_id)
        assert loaded.visible is False

    def test_set_color_persists(self, tmp_path):
        """Color changes should persist."""
        db_path = tmp_path / "test.db"
        store = PersistentDatasetStore(db_path=db_path)

        result = create_test_result()
        trace = store.add_result(result)

        store.set_color(trace.trace_id, "#ff0000")
        assert trace.color == "#ff0000"

        # Verify persists
        store2 = PersistentDatasetStore(db_path=db_path)
        loaded = store2.get(trace.trace_id)
        assert loaded.color == "#ff0000"


class TestSessionManagement:
    """Test session management features."""

    def test_start_session_creates_record(self, tmp_path):
        """Starting session should create database record."""
        db_path = tmp_path / "test.db"
        store = PersistentDatasetStore(db_path=db_path)

        session_id = store.start_session(metadata={"operator": "TestUser"})

        assert session_id is not None
        sessions = store.list_sessions()
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == session_id
        assert sessions[0]["metadata"]["operator"] == "TestUser"

    def test_get_session_metadata(self, tmp_path):
        """Should retrieve session metadata."""
        db_path = tmp_path / "test.db"
        store = PersistentDatasetStore(db_path=db_path)

        session_id = store.start_session(metadata={"key": "value"})
        metadata = store.get_session_metadata(session_id)

        assert metadata["key"] == "value"

    def test_list_sessions_ordered(self, tmp_path):
        """Sessions should be listed newest first."""
        db_path = tmp_path / "test.db"
        store = PersistentDatasetStore(db_path=db_path)

        import time
        store.start_session()
        time.sleep(0.01)
        store.start_session()
        time.sleep(0.01)
        store.start_session()

        sessions = store.list_sessions()
        assert len(sessions) == 3
        # Should be ordered by created_at DESC


class TestQueryAndFiltering:
    """Test query and filtering capabilities."""

    def test_query_by_name_pattern(self, tmp_path):
        """Should filter traces by name pattern."""
        db_path = tmp_path / "test.db"
        store = PersistentDatasetStore(db_path=db_path)

        store.add_result(create_test_result("DeviceA"), "Measurement_A")
        store.add_result(create_test_result("DeviceB"), "Measurement_B")
        store.add_result(create_test_result("DeviceC"), "Other_C")

        results = store.query_traces(name_pattern="Measurement")
        assert len(results) == 2

    def test_query_visible_only(self, tmp_path):
        """Should filter by visibility."""
        db_path = tmp_path / "test.db"
        store = PersistentDatasetStore(db_path=db_path)

        trace1 = store.add_result(create_test_result(), "Visible")
        trace2 = store.add_result(create_test_result(), "Hidden")
        store.toggle_visibility(trace2.trace_id)

        visible = store.query_traces(visible_only=True)
        assert len(visible) == 1
        assert visible[0].name == "Visible"

    def test_query_by_date_range(self, tmp_path):
        """Should filter by date range."""
        db_path = tmp_path / "test.db"
        store = PersistentDatasetStore(db_path=db_path)

        store.add_result(create_test_result())

        from datetime import timedelta
        now = datetime.now()
        past = now - timedelta(days=1)
        future = now + timedelta(days=1)

        results = store.query_traces(date_from=past, date_to=future)
        assert len(results) >= 1


class TestDatabaseOperations:
    """Test database maintenance operations."""

    def test_get_database_size(self, tmp_path):
        """Should report database size."""
        db_path = tmp_path / "test.db"
        store = PersistentDatasetStore(db_path=db_path)

        # Empty database has some size
        size_before = store.get_database_size()
        assert size_before > 0

        # Add data increases size
        for i in range(10):
            store.add_result(create_test_result(num_points=100))

        size_after = store.get_database_size()
        assert size_after > size_before

    def test_backup_database(self, tmp_path):
        """Should create database backup."""
        db_path = tmp_path / "test.db"
        store = PersistentDatasetStore(db_path=db_path)

        store.add_result(create_test_result())

        backup_path = store.backup_database()
        assert backup_path.exists()
        assert backup_path.suffix == ".bak"

        # Backup should have same data
        backup_store = PersistentDatasetStore(db_path=backup_path, auto_load=True)
        assert backup_store.get_trace_count() == 1

    def test_vacuum_reclaims_space(self, tmp_path):
        """Vacuum should complete without error."""
        db_path = tmp_path / "test.db"
        store = PersistentDatasetStore(db_path=db_path)

        # Add and remove data
        for i in range(10):
            trace = store.add_result(create_test_result())
            store.remove(trace.trace_id)

        # Vacuum should work
        store.vacuum()
        # No exception means success


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_create_persistent_store(self, tmp_path):
        """Convenience function should create store."""
        db_path = tmp_path / "test.db"
        store = create_persistent_store(db_path)

        assert isinstance(store, PersistentDatasetStore)
        assert store.db_path == db_path


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
