"""Unit tests for waveform tools."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from pywellen_mcp.session import SessionManager
from pywellen_mcp.tools_waveform import WaveformTools
from pywellen_mcp.errors import FileError, SessionError, ErrorCode


class MockHierarchy:
    """Mock Hierarchy object."""

    def __init__(self):
        self._format = "VCD"
        self._timescale = None
        self._date = "2024-01-01"
        self._version = "test-1.0"

    def file_format(self):
        return self._format

    def timescale(self):
        return self._timescale

    def date(self):
        return self._date

    def version(self):
        return self._version

    def all_vars(self):
        return iter([Mock(), Mock(), Mock()])

    def top_scopes(self):
        return iter([Mock()])


class MockWaveform:
    """Mock Waveform object."""

    def __init__(self, path: str, multi_threaded: bool = True, remove_scopes_with_empty_name: bool = False, **kwargs):
        self.hierarchy = MockHierarchy()
        self.time_table = Mock()
        # Mock time_table indexing - raise IndexError after 10 items to prevent infinite loops
        def mock_getitem(i):
            if i >= 10:
                raise IndexError(f"Index {i} out of range")
            return i * 100
        self.time_table.__getitem__ = Mock(side_effect=mock_getitem)


@pytest.fixture
def mock_waveform():
    """Fixture for mock Waveform."""
    with patch("pywellen_mcp.session.Waveform", MockWaveform):
        yield MockWaveform


@pytest.fixture
def session_manager():
    """Fixture for SessionManager."""
    return SessionManager(max_sessions=5)


@pytest.fixture
def waveform_tools(session_manager):
    """Fixture for WaveformTools."""
    return WaveformTools(session_manager)


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary test file."""
    test_file = tmp_path / "test.vcd"
    test_file.write_text("# dummy vcd content")
    return test_file


class TestWaveformOpen:
    """Test waveform_open tool."""

    @pytest.mark.asyncio
    async def test_open_success(self, waveform_tools, temp_file, mock_waveform):
        """Test successful waveform opening."""
        result = await waveform_tools.waveform_open(str(temp_file))

        assert "session_id" in result
        assert result["format"] == "VCD"
        assert result["path"] == str(temp_file.absolute())
        assert result["num_variables"] == 3
        assert "time_range" in result

    @pytest.mark.asyncio
    async def test_open_with_options(self, waveform_tools, temp_file, mock_waveform):
        """Test opening with custom options."""
        result = await waveform_tools.waveform_open(
            str(temp_file),
            multi_threaded=False,
            remove_empty_scopes=True,
        )

        assert "session_id" in result
        session = waveform_tools.session_manager.get_session(result["session_id"])
        assert session is not None
        assert session.multi_threaded is False
        assert session.remove_scopes_with_empty_name is True

    @pytest.mark.asyncio
    async def test_open_file_not_found(self, waveform_tools):
        """Test opening non-existent file."""
        with pytest.raises(FileError) as exc_info:
            await waveform_tools.waveform_open("/nonexistent/file.vcd")

        assert exc_info.value.code == ErrorCode.FILE_NOT_FOUND
        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_open_directory_instead_of_file(self, waveform_tools, tmp_path):
        """Test opening a directory instead of file."""
        with pytest.raises(FileError) as exc_info:
            await waveform_tools.waveform_open(str(tmp_path))

        assert exc_info.value.code == ErrorCode.INVALID_PARAMETER
        assert "not a file" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_open_metadata_included(self, waveform_tools, temp_file, mock_waveform):
        """Test that metadata is included in response."""
        result = await waveform_tools.waveform_open(str(temp_file))

        assert "date" in result
        assert result["date"] == "2024-01-01"
        assert "version" in result
        assert result["version"] == "test-1.0"


class TestWaveformInfo:
    """Test waveform_info tool."""

    @pytest.mark.asyncio
    async def test_info_success(self, waveform_tools, temp_file, mock_waveform):
        """Test getting waveform info."""
        # First open a file
        open_result = await waveform_tools.waveform_open(str(temp_file))
        session_id = open_result["session_id"]

        # Get info
        info = await waveform_tools.waveform_info(session_id)

        assert info["session_id"] == session_id
        assert info["format"] == "VCD"
        assert "created_at" in info
        assert "last_accessed" in info
        assert info["num_variables"] == 3
        assert info["num_top_scopes"] == 1

    @pytest.mark.asyncio
    async def test_info_session_not_found(self, waveform_tools):
        """Test getting info for non-existent session."""
        with pytest.raises(SessionError) as exc_info:
            await waveform_tools.waveform_info("invalid-session-id")

        assert exc_info.value.code == ErrorCode.SESSION_NOT_FOUND


class TestWaveformClose:
    """Test waveform_close tool."""

    @pytest.mark.asyncio
    async def test_close_success(self, waveform_tools, temp_file, mock_waveform):
        """Test closing a session."""
        # Open a file
        open_result = await waveform_tools.waveform_open(str(temp_file))
        session_id = open_result["session_id"]

        # Close it
        close_result = await waveform_tools.waveform_close(session_id)

        assert close_result["success"] is True
        assert close_result["session_id"] == session_id

        # Verify it's gone
        assert waveform_tools.session_manager.get_session(session_id) is None

    @pytest.mark.asyncio
    async def test_close_session_not_found(self, waveform_tools):
        """Test closing non-existent session."""
        with pytest.raises(SessionError) as exc_info:
            await waveform_tools.waveform_close("invalid-session-id")

        assert exc_info.value.code == ErrorCode.SESSION_NOT_FOUND


class TestWaveformListSessions:
    """Test waveform_list_sessions tool."""

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, waveform_tools):
        """Test listing when no sessions exist."""
        result = await waveform_tools.waveform_list_sessions()

        assert result["count"] == 0
        assert result["sessions"] == []
        assert "max_sessions" in result

    @pytest.mark.asyncio
    async def test_list_sessions_multiple(self, waveform_tools, temp_file, mock_waveform):
        """Test listing multiple sessions."""
        # Open multiple files
        session1 = await waveform_tools.waveform_open(str(temp_file))
        session2 = await waveform_tools.waveform_open(str(temp_file))

        # List sessions
        result = await waveform_tools.waveform_list_sessions()

        assert result["count"] == 2
        assert session1["session_id"] in result["sessions"]
        assert session2["session_id"] in result["sessions"]
