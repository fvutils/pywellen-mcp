"""Unit tests for session management."""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from pywellen_mcp.session import SessionManager, WaveformSession


class MockWaveform:
    """Mock Waveform object for testing."""

    def __init__(self, path: str, multi_threaded: bool = True, remove_scopes_with_empty_name: bool = False):
        self.hierarchy = Mock()
        self.time_table = Mock()
        self.hierarchy.file_format.return_value = "VCD"
        self.hierarchy.timescale.return_value = None
        self.hierarchy.date.return_value = "2024-01-01"
        self.hierarchy.version.return_value = "test-1.0"
        self.hierarchy.all_vars.return_value = iter([])


@pytest.fixture
def mock_waveform():
    """Fixture for mock Waveform."""
    with patch("pywellen_mcp.session.Waveform", MockWaveform):
        yield MockWaveform


@pytest.fixture
def session_manager():
    """Fixture for SessionManager."""
    return SessionManager(max_sessions=3, session_timeout=timedelta(seconds=10))


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary test file."""
    test_file = tmp_path / "test.vcd"
    test_file.write_text("# dummy vcd content")
    return test_file


class TestSessionManager:
    """Test cases for SessionManager."""

    def test_create_session_success(self, session_manager, temp_file, mock_waveform):
        """Test successful session creation."""
        session = session_manager.create_session(str(temp_file))

        assert session.session_id is not None
        assert len(session.session_id) == 36  # UUID format
        assert session.filepath == temp_file
        assert session.waveform is not None
        assert session.hierarchy is not None
        assert session.time_table is not None
        assert session.multi_threaded is True
        assert session.remove_scopes_with_empty_name is False

    def test_create_session_file_not_found(self, session_manager, mock_waveform):
        """Test session creation with non-existent file."""
        with pytest.raises(FileNotFoundError):
            session_manager.create_session("/nonexistent/file.vcd")

    def test_create_session_max_sessions(self, session_manager, temp_file, mock_waveform):
        """Test session limit enforcement."""
        # Create max sessions
        for i in range(3):
            session_manager.create_session(str(temp_file))

        assert session_manager.get_session_count() == 3

        # Try to create one more
        with pytest.raises(RuntimeError, match="Maximum number of sessions"):
            session_manager.create_session(str(temp_file))

    def test_get_session(self, session_manager, temp_file, mock_waveform):
        """Test retrieving a session."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        retrieved = session_manager.get_session(session_id)
        assert retrieved is not None
        assert retrieved.session_id == session_id

    def test_get_session_not_found(self, session_manager):
        """Test retrieving non-existent session."""
        result = session_manager.get_session("invalid-id")
        assert result is None

    def test_get_session_updates_access_time(self, session_manager, temp_file, mock_waveform):
        """Test that get_session updates last_accessed."""
        session = session_manager.create_session(str(temp_file))
        original_time = session.last_accessed

        # Wait a bit and retrieve
        import time

        time.sleep(0.1)
        retrieved = session_manager.get_session(session.session_id)

        assert retrieved is not None
        assert retrieved.last_accessed > original_time

    def test_close_session(self, session_manager, temp_file, mock_waveform):
        """Test closing a session."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        success = session_manager.close_session(session_id)
        assert success is True
        assert session_manager.get_session(session_id) is None

    def test_close_session_not_found(self, session_manager):
        """Test closing non-existent session."""
        success = session_manager.close_session("invalid-id")
        assert success is False

    def test_list_sessions(self, session_manager, temp_file, mock_waveform):
        """Test listing sessions."""
        session1 = session_manager.create_session(str(temp_file))
        session2 = session_manager.create_session(str(temp_file))

        sessions = session_manager.list_sessions()
        assert len(sessions) == 2
        assert session1.session_id in sessions
        assert session2.session_id in sessions

    def test_cleanup_expired_sessions(self, session_manager, temp_file, mock_waveform):
        """Test automatic cleanup of expired sessions."""
        # Create sessions
        session1 = session_manager.create_session(str(temp_file))
        session2 = session_manager.create_session(str(temp_file))

        # Manually expire first session
        session1.last_accessed = datetime.now() - timedelta(seconds=20)

        # Trigger cleanup
        removed = session_manager._cleanup_expired()

        assert removed == 1
        assert session_manager.get_session(session1.session_id) is None
        assert session_manager.get_session(session2.session_id) is not None

    def test_cleanup_all(self, session_manager, temp_file, mock_waveform):
        """Test cleanup of all sessions."""
        session_manager.create_session(str(temp_file))
        session_manager.create_session(str(temp_file))

        count = session_manager.cleanup_all()
        assert count == 2
        assert session_manager.get_session_count() == 0


class TestWaveformSession:
    """Test cases for WaveformSession."""

    def test_update_access_time(self):
        """Test updating access time."""
        session = WaveformSession(
            session_id="test-id",
            filepath=Path("/test/file.vcd"),
            waveform=Mock(),
            hierarchy=Mock(),
            time_table=Mock(),
            created_at=datetime.now(),
            last_accessed=datetime.now(),
        )

        original_time = session.last_accessed
        import time

        time.sleep(0.1)
        session.update_access_time()

        assert session.last_accessed > original_time

    def test_is_expired(self):
        """Test expiration check."""
        now = datetime.now()
        session = WaveformSession(
            session_id="test-id",
            filepath=Path("/test/file.vcd"),
            waveform=Mock(),
            hierarchy=Mock(),
            time_table=Mock(),
            created_at=now,
            last_accessed=now - timedelta(seconds=20),
        )

        assert session.is_expired(timedelta(seconds=10)) is True
        assert session.is_expired(timedelta(seconds=30)) is False
