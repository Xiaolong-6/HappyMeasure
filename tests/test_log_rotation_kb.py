"""Test that log rotation KB setting works immediately."""
import tempfile
from pathlib import Path
from keith_ivt.data.logging_utils import AppLog


def test_log_rotation_kb_immediate():
    """Verify that changing max_bytes triggers immediate rotation if needed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "log.txt"

        # Create a log with ~2KB
        log = AppLog(path=log_path, max_bytes=5000)
        log.write("x" * 2000)  # Write enough to get ~2KB

        assert log_path.exists()
        initial_size = log_path.stat().st_size
        assert initial_size > 1024, f"Initial file should be > 1KB, got {initial_size}"

        # Now reduce the limit to 1KB (1024 bytes) - should trigger immediate rotation
        log.set_max_bytes(1024)

        # The old file should have been rotated away
        rotated_files = list(Path(tmpdir).glob("log_*.txt"))
        assert len(rotated_files) == 1, f"Expected 1 rotated file, found {len(rotated_files)}"

        # After rotation, log.txt may not exist until next write (which is OK)
        # Write something new - this should create a fresh log.txt
        log.write("new message after rotation")
        assert log_path.exists(), "New log.txt should be created after writing"

        content = log_path.read_text(encoding="utf-8")
        assert "new message after rotation" in content

        # Verify the rotated file has the old content
        rotated_content = rotated_files[0].read_text(encoding="utf-8")
        assert "x" * 100 in rotated_content, "Rotated file should contain the old data"


if __name__ == "__main__":
    test_log_rotation_kb_immediate()
    print("OK - Log rotation KB setting works correctly!")
