"""Unit tests for signal data access tools."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from pywellen_mcp.session import SessionManager
from pywellen_mcp.tools_signal import SignalTools, SignalCache
from pywellen_mcp.errors import SessionError, QueryError, ErrorCode


class MockSignal:
    """Mock signal object."""

    def __init__(self, changes_data):
        """
        Args:
            changes_data: List of (time_idx, value) tuples
        """
        self._changes = changes_data

    def value_at_time(self, time):
        """Get value at specific time."""
        # Find closest time <= requested time
        for time_idx, value in self._changes:
            # Convert time_idx to time (multiply by 100 for our mock)
            actual_time = time_idx * 100
            if actual_time == time:
                return value
        raise ValueError(f"No value at time {time}")

    def value_at_idx(self, idx):
        """Get value at time index."""
        for time_idx, value in self._changes:
            if time_idx == idx:
                return value
        return None

    def all_changes(self):
        """Iterate all changes."""
        return iter(self._changes)


class MockWaveform:
    """Mock waveform with signals."""

    def __init__(self, path: str, multi_threaded: bool = True, remove_scopes_with_empty_name: bool = False, **kwargs):
        # Define some signals
        self._signals = {
            "top.clk": MockSignal([
                (0, "0"),
                (5, "1"),
                (10, "0"),
                (15, "1"),
                (20, "0"),
            ]),
            "top.data": MockSignal([
                (0, "0x00"),
                (10, "0x42"),
                (20, "0xFF"),
            ]),
            "top.count": MockSignal([
                (0, 0),
                (5, 1),
                (10, 2),
                (15, 3),
                (20, 4),
            ]),
        }

        self.hierarchy = Mock()
        self.time_table = Mock()
        # Mock time_table: index * 100 = time
        def mock_getitem(i):
            if i >= 25:
                raise IndexError(f"Index {i} out of range")
            return i * 100
        self.time_table.__getitem__ = Mock(side_effect=mock_getitem)

    def get_signal_from_path(self, path):
        """Get signal by path."""
        if path in self._signals:
            return self._signals[path]
        raise ValueError(f"Signal not found: {path}")


@pytest.fixture
def mock_waveform():
    """Fixture for mock waveform."""
    with patch("pywellen_mcp.session.Waveform", MockWaveform):
        yield MockWaveform


@pytest.fixture
def session_manager():
    """Fixture for SessionManager."""
    return SessionManager(max_sessions=5)


@pytest.fixture
def signal_tools(session_manager):
    """Fixture for SignalTools."""
    return SignalTools(session_manager, cache_size=10)


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary test file."""
    test_file = tmp_path / "test.vcd"
    test_file.write_text("# dummy vcd content")
    return test_file


class TestSignalCache:
    """Test SignalCache."""

    def test_cache_put_get(self):
        """Test basic cache operations."""
        cache = SignalCache(max_size=2)
        signal = Mock()

        cache.put("session1", "signal1", signal)
        assert cache.get("session1", "signal1") == signal

    def test_cache_lru_eviction(self):
        """Test LRU eviction."""
        cache = SignalCache(max_size=2)
        signal1 = Mock()
        signal2 = Mock()
        signal3 = Mock()

        cache.put("session1", "signal1", signal1)
        cache.put("session1", "signal2", signal2)
        
        # Access signal1 to make it more recent
        cache.get("session1", "signal1")
        
        # Add signal3, should evict signal2
        cache.put("session1", "signal3", signal3)
        
        assert cache.get("session1", "signal1") == signal1
        assert cache.get("session1", "signal2") is None
        assert cache.get("session1", "signal3") == signal3

    def test_cache_clear_session(self):
        """Test clearing session from cache."""
        cache = SignalCache(max_size=10)
        
        cache.put("session1", "signal1", Mock())
        cache.put("session1", "signal2", Mock())
        cache.put("session2", "signal1", Mock())
        
        cleared = cache.clear_session("session1")
        assert cleared == 2
        assert cache.get("session1", "signal1") is None
        assert cache.get("session2", "signal1") is not None


class TestSignalGetValue:
    """Test signal_get_value tool."""

    @pytest.mark.asyncio
    async def test_get_value_single_time(self, signal_tools, temp_file, mock_waveform, session_manager):
        """Test querying single time."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        result = await signal_tools.signal_get_value(
            session_id,
            "top.clk",
            times=500,
        )

        assert result["session_id"] == session_id
        assert result["variable_path"] == "top.clk"
        assert len(result["values"]) == 1
        assert result["values"][0]["time"] == 500
        assert result["values"][0]["value"] == "1"

    @pytest.mark.asyncio
    async def test_get_value_multiple_times(self, signal_tools, temp_file, mock_waveform, session_manager):
        """Test querying multiple times."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        result = await signal_tools.signal_get_value(
            session_id,
            "top.count",
            times=[0, 500, 1000],
        )

        assert len(result["values"]) == 3
        assert result["values"][0]["value"] == 0
        assert result["values"][1]["value"] == 1
        assert result["values"][2]["value"] == 2

    @pytest.mark.asyncio
    async def test_get_value_with_format(self, signal_tools, temp_file, mock_waveform, session_manager):
        """Test value formatting."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        result = await signal_tools.signal_get_value(
            session_id,
            "top.count",
            times=1000,
            format="hex",
        )

        assert result["values"][0]["value"] == "0x2"

    @pytest.mark.asyncio
    async def test_get_value_signal_not_found(self, signal_tools, temp_file, mock_waveform, session_manager):
        """Test with non-existent signal."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        with pytest.raises(QueryError) as exc_info:
            await signal_tools.signal_get_value(session_id, "top.nonexistent", times=0)
        assert exc_info.value.code == ErrorCode.SIGNAL_NOT_FOUND


class TestSignalGetChanges:
    """Test signal_get_changes tool."""

    @pytest.mark.asyncio
    async def test_get_all_changes(self, signal_tools, temp_file, mock_waveform, session_manager):
        """Test getting all changes."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        result = await signal_tools.signal_get_changes(
            session_id,
            "top.clk",
        )

        assert result["session_id"] == session_id
        assert result["count"] == 5
        assert len(result["changes"]) == 5
        assert result["changes"][0]["time"] == 0
        assert result["changes"][0]["value"] == "0"

    @pytest.mark.asyncio
    async def test_get_changes_with_time_range(self, signal_tools, temp_file, mock_waveform, session_manager):
        """Test filtering by time range."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        result = await signal_tools.signal_get_changes(
            session_id,
            "top.clk",
            start_time=500,
            end_time=1500,
        )

        # Should get changes at 500, 1000, 1500
        assert result["count"] == 3
        assert result["changes"][0]["time"] == 500
        assert result["changes"][-1]["time"] == 1500

    @pytest.mark.asyncio
    async def test_get_changes_with_limit(self, signal_tools, temp_file, mock_waveform, session_manager):
        """Test limiting number of changes."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        result = await signal_tools.signal_get_changes(
            session_id,
            "top.clk",
            max_changes=3,
        )

        assert result["count"] == 3
        assert result["truncated"] is True

    @pytest.mark.asyncio
    async def test_get_changes_invalid_range(self, signal_tools, temp_file, mock_waveform, session_manager):
        """Test with invalid time range."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        with pytest.raises(QueryError) as exc_info:
            await signal_tools.signal_get_changes(
                session_id,
                "top.clk",
                start_time=1000,
                end_time=500,
            )
        assert exc_info.value.code == ErrorCode.INVALID_TIME_RANGE


class TestTimeGetRange:
    """Test time_get_range tool."""

    @pytest.mark.asyncio
    async def test_get_time_range(self, signal_tools, temp_file, mock_waveform, session_manager):
        """Test getting time range."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        result = await signal_tools.time_get_range(session_id)

        assert result["session_id"] == session_id
        assert result["min_time"] == 0
        assert result["max_time"] == 2400  # Last valid index is 24
        assert result["num_time_points"] == 25


class TestTimeConvert:
    """Test time_convert tool."""

    @pytest.mark.asyncio
    async def test_convert_indices_to_times(self, signal_tools, temp_file, mock_waveform, session_manager):
        """Test converting indices to times."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        result = await signal_tools.time_convert(
            session_id,
            indices=[0, 5, 10],
        )

        assert "index_to_time" in result
        assert len(result["index_to_time"]) == 3
        assert result["index_to_time"][0]["time"] == 0
        assert result["index_to_time"][1]["time"] == 500
        assert result["index_to_time"][2]["time"] == 1000

    @pytest.mark.asyncio
    async def test_convert_times_to_indices(self, signal_tools, temp_file, mock_waveform, session_manager):
        """Test converting times to indices."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        result = await signal_tools.time_convert(
            session_id,
            times=[0, 500, 1000],
        )

        assert "time_to_index" in result
        assert len(result["time_to_index"]) == 3
        assert result["time_to_index"][0]["index"] == 0
        assert result["time_to_index"][0]["exact"] is True

    @pytest.mark.asyncio
    async def test_convert_no_params(self, signal_tools, temp_file, mock_waveform, session_manager):
        """Test with no conversion parameters."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        with pytest.raises(QueryError) as exc_info:
            await signal_tools.time_convert(session_id)
        assert exc_info.value.code == ErrorCode.INVALID_PARAMETER


class TestSignalGetStatistics:
    """Test signal_get_statistics tool."""

    @pytest.mark.asyncio
    async def test_get_statistics(self, signal_tools, temp_file, mock_waveform, session_manager):
        """Test computing statistics."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        result = await signal_tools.signal_get_statistics(
            session_id,
            "top.count",
        )

        assert result["num_changes"] == 5
        assert result["num_unique_values"] == 5
        assert result["first_change_time"] == 0
        assert result["last_change_time"] == 2000
        assert "numeric_statistics" in result
        assert result["numeric_statistics"]["min_value"] == 0
        assert result["numeric_statistics"]["max_value"] == 4

    @pytest.mark.asyncio
    async def test_get_statistics_with_range(self, signal_tools, temp_file, mock_waveform, session_manager):
        """Test statistics with time range."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        result = await signal_tools.signal_get_statistics(
            session_id,
            "top.count",
            start_time=500,
            end_time=1500,
        )

        # Should get changes at 500, 1000, 1500
        assert result["num_changes"] == 3
        assert result["first_change_time"] == 500
