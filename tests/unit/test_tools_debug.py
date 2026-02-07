"""Tests for debugging and analysis tools."""

import pytest
from unittest.mock import Mock, MagicMock
from pywellen_mcp.tools_debug import (
    debug_find_transition,
    debug_trace_causality,
    debug_event_timeline,
    search_by_activity,
    signal_compare,
)
from pywellen_mcp.session import SessionManager
from pywellen_mcp.errors import QueryError


class MockSignal:
    """Mock signal with predefined changes."""
    
    def __init__(self, changes):
        """
        Args:
            changes: List of (time_idx, value) tuples
        """
        self._changes = changes
    
    def all_changes(self):
        """Return iterator of changes."""
        return iter(self._changes)
    
    def value_at_time(self, time):
        """Get value at specific time."""
        # Find most recent change before or at time
        result = None
        for time_idx, value in self._changes:
            change_time = time_idx * 100  # Mock time table mapping
            if change_time <= time:
                result = value
            else:
                break
        return result


class MockWaveform:
    """Mock waveform with multiple signals."""
    
    def __init__(self):
        self.signals = {
            "top.clk": MockSignal([
                (0, "0"), (1, "1"), (2, "0"), (3, "1"), (4, "0"), (5, "1")
            ]),
            "top.reset": MockSignal([
                (0, "1"), (2, "0")
            ]),
            "top.state": MockSignal([
                (0, "0"), (3, "1"), (5, "2"), (7, "3")
            ]),
            "top.counter": MockSignal([
                (0, "0"), (2, "5"), (4, "10"), (6, "15")
            ]),
            "top.enable": MockSignal([
                (1, "0"), (4, "1"), (8, "0")
            ]),
            "top.cpu.data": MockSignal([
                (2, "0xAA"), (5, "0xBB")
            ]),
        }
    
    def get_signal_from_path(self, path):
        """Get signal by path."""
        if path in self.signals:
            return self.signals[path]
        raise ValueError(f"Signal not found: {path}")
    
    def get_signal(self, var):
        """Get signal by variable."""
        path = var.full_name(None)
        return self.get_signal_from_path(path)


class MockVar:
    """Mock variable."""
    
    def __init__(self, path):
        self._path = path
    
    def full_name(self, hier):
        return self._path


class MockScope:
    """Mock scope."""
    
    def __init__(self, variables):
        self._variables = [MockVar(path) for path in variables]
    
    def vars(self, hier):
        return iter(self._variables)


class MockHierarchy:
    """Mock hierarchy."""
    
    def __init__(self):
        self.scopes = {
            "top": MockScope([
                "top.clk", "top.reset", "top.state", "top.counter", "top.enable"
            ]),
            "top.cpu": MockScope([
                "top.cpu.data"
            ]),
        }
    
    def all_vars(self):
        """Return all variables."""
        all_vars = []
        for scope in self.scopes.values():
            all_vars.extend(scope.vars(None))
        return iter(all_vars)


@pytest.fixture
def session_manager():
    """Create session manager with mock session."""
    manager = SessionManager(max_sessions=5)
    
    # Create mock session
    session = Mock()
    session.waveform = MockWaveform()
    session.hierarchy = MockHierarchy()
    
    # Mock time table (index * 100 = time)
    time_table = Mock()
    def time_table_getitem(self, idx):
        if idx > 10:
            raise IndexError("Out of range")
        return idx * 100
    time_table.__getitem__ = time_table_getitem
    session.time_table = time_table
    
    manager._sessions["test-session"] = session
    
    return manager


@pytest.mark.asyncio
class TestDebugFindTransition:
    """Tests for debug_find_transition tool."""
    
    async def test_find_rises(self, session_manager):
        """Test finding rising edges."""
        result = await debug_find_transition(
            session_manager,
            "test-session",
            "top.clk",
            condition="rises",
        )
        
        assert result["count"] == 3
        assert not result["truncated"]
        transitions = result["transitions"]
        assert transitions[0]["time"] == 100
        assert transitions[0]["value"] == "1"
        assert transitions[0]["prev_value"] == "0"
    
    async def test_find_falls(self, session_manager):
        """Test finding falling edges."""
        result = await debug_find_transition(
            session_manager,
            "test-session",
            "top.clk",
            condition="falls",
        )
        
        assert result["count"] == 2  # Falls at indices 2 and 4
        transitions = result["transitions"]
        assert transitions[0]["time"] == 200
        assert transitions[0]["value"] == "0"
        assert transitions[0]["prev_value"] == "1"
    
    async def test_find_equals(self, session_manager):
        """Test finding specific value."""
        result = await debug_find_transition(
            session_manager,
            "test-session",
            "top.state",
            condition="equals",
            value="2",
        )
        
        assert result["count"] == 1
        assert result["transitions"][0]["time"] == 500
        assert result["transitions"][0]["value"] == "2"
    
    async def test_find_greater(self, session_manager):
        """Test finding values greater than threshold."""
        result = await debug_find_transition(
            session_manager,
            "test-session",
            "top.counter",
            condition="greater",
            value="5",
        )
        
        assert result["count"] >= 1
        assert all(int(t["value"]) > 5 for t in result["transitions"])
    
    async def test_time_window(self, session_manager):
        """Test filtering by time window."""
        result = await debug_find_transition(
            session_manager,
            "test-session",
            "top.clk",
            condition="rises",
            start_time=200,
            end_time=400,
        )
        
        assert result["count"] == 1
        assert result["transitions"][0]["time"] == 300
    
    async def test_max_results(self, session_manager):
        """Test max_results limiting."""
        result = await debug_find_transition(
            session_manager,
            "test-session",
            "top.clk",
            condition="rises",
            max_results=2,
        )
        
        assert result["count"] == 2
        assert result["truncated"]
    
    async def test_invalid_signal(self, session_manager):
        """Test error handling for invalid signal."""
        with pytest.raises(QueryError):
            await debug_find_transition(
                session_manager,
                "test-session",
                "top.nonexistent",
                condition="rises",
            )
    
    async def test_missing_value_parameter(self, session_manager):
        """Test error when value required but not provided."""
        with pytest.raises(QueryError):
            await debug_find_transition(
                session_manager,
                "test-session",
                "top.state",
                condition="equals",
            )


@pytest.mark.asyncio
class TestDebugTraceCausality:
    """Tests for debug_trace_causality tool."""
    
    async def test_find_potential_causes(self, session_manager):
        """Test finding signals that changed before target."""
        result = await debug_trace_causality(
            session_manager,
            "test-session",
            target_path="top.state",
            target_time=300,
            search_window=200,
            related_signals=["top.clk", "top.reset", "top.enable"],  # Explicitly provide signals
        )
        
        assert result["target"]["path"] == "top.state"
        assert result["target"]["time"] == 300
        assert len(result["potential_causes"]) > 0
        
        # Verify all causes happened before target
        for cause in result["potential_causes"]:
            assert cause["time"] < 300
            assert cause["delta_time"] >= 0
            assert 0 <= cause["relevance"] <= 1
    
    async def test_relevance_scoring(self, session_manager):
        """Test that closer changes have higher relevance."""
        result = await debug_trace_causality(
            session_manager,
            "test-session",
            target_path="top.state",
            target_time=300,
            search_window=300,
        )
        
        # Relevance should be sorted descending
        causes = result["potential_causes"]
        if len(causes) > 1:
            for i in range(len(causes) - 1):
                assert causes[i]["relevance"] >= causes[i + 1]["relevance"]
    
    async def test_with_related_signals(self, session_manager):
        """Test with explicit list of related signals."""
        result = await debug_trace_causality(
            session_manager,
            "test-session",
            target_path="top.state",
            target_time=500,
            search_window=400,
            related_signals=["top.clk", "top.enable"],
        )
        
        # Should only include specified signals
        causes = result["potential_causes"]
        for cause in causes:
            assert cause["path"] in ["top.clk", "top.enable"]


@pytest.mark.asyncio
class TestDebugEventTimeline:
    """Tests for debug_event_timeline tool."""
    
    async def test_build_timeline(self, session_manager):
        """Test building chronological event timeline."""
        result = await debug_event_timeline(
            session_manager,
            "test-session",
            signal_paths=["top.clk", "top.reset", "top.state"],
            start_time=0,
            end_time=600,
        )
        
        assert result["count"] > 0
        assert not result["truncated"]
        
        # Verify events are sorted by time
        events = result["events"]
        for i in range(len(events) - 1):
            assert events[i]["time"] <= events[i + 1]["time"]
    
    async def test_timeline_contains_all_signals(self, session_manager):
        """Test that timeline includes events from all signals."""
        result = await debug_event_timeline(
            session_manager,
            "test-session",
            signal_paths=["top.clk", "top.state"],
            start_time=0,
            end_time=600,
        )
        
        # Should have events from both signals
        signal_set = {event["signal"] for event in result["events"]}
        assert "top.clk" in signal_set
        assert "top.state" in signal_set
    
    async def test_max_events_limit(self, session_manager):
        """Test max_events limiting."""
        result = await debug_event_timeline(
            session_manager,
            "test-session",
            signal_paths=["top.clk", "top.reset", "top.state"],
            start_time=0,
            end_time=600,
            max_events=5,
        )
        
        assert result["count"] == 5
        assert result["truncated"]


@pytest.mark.asyncio
class TestSearchByActivity:
    """Tests for search_by_activity tool."""
    
    async def test_find_all_signals(self, session_manager):
        """Test finding all signals without filters."""
        result = await search_by_activity(
            session_manager,
            "test-session",
        )
        
        assert result["count"] > 0
        assert all("toggle_count" in s for s in result["signals"])
        assert all("toggle_rate" in s for s in result["signals"])
    
    async def test_min_toggles_filter(self, session_manager):
        """Test filtering by minimum toggle count."""
        result = await search_by_activity(
            session_manager,
            "test-session",
            min_toggles=3,
        )
        
        # All results should have at least 3 toggles
        for signal in result["signals"]:
            assert signal["toggle_count"] >= 3
    
    async def test_max_toggles_filter(self, session_manager):
        """Test filtering by maximum toggle count."""
        result = await search_by_activity(
            session_manager,
            "test-session",
            max_toggles=2,
        )
        
        # All results should have at most 2 toggles
        for signal in result["signals"]:
            assert signal["toggle_count"] <= 2
    
    async def test_sorted_by_activity(self, session_manager):
        """Test results sorted by toggle count."""
        result = await search_by_activity(
            session_manager,
            "test-session",
        )
        
        # Should be sorted descending
        signals = result["signals"]
        if len(signals) > 1:
            for i in range(len(signals) - 1):
                assert signals[i]["toggle_count"] >= signals[i + 1]["toggle_count"]


@pytest.mark.asyncio
class TestSignalCompare:
    """Tests for signal_compare tool."""
    
    async def test_identical_signals(self, session_manager):
        """Test comparing identical signals."""
        # Use same signal for both
        result = await signal_compare(
            session_manager,
            "test-session",
            "top.clk",
            "top.clk",
        )
        
        assert result["difference_count"] == 0
        assert result["match_percentage"] == 100.0
        assert result["first_difference_time"] is None
    
    async def test_different_signals(self, session_manager):
        """Test comparing different signals."""
        result = await signal_compare(
            session_manager,
            "test-session",
            "top.clk",
            "top.reset",
        )
        
        assert result["difference_count"] > 0
        assert result["match_percentage"] < 100.0
        assert result["first_difference_time"] is not None
    
    async def test_difference_details(self, session_manager):
        """Test difference details in results."""
        result = await signal_compare(
            session_manager,
            "test-session",
            "top.clk",
            "top.enable",
            start_time=0,
            end_time=500,
        )
        
        # Should have difference details
        if result["difference_count"] > 0:
            diff = result["differences"][0]
            assert "time" in diff
            assert "value1" in diff
            assert "value2" in diff
    
    async def test_time_window(self, session_manager):
        """Test comparing within time window."""
        result = await signal_compare(
            session_manager,
            "test-session",
            "top.state",
            "top.counter",
            start_time=200,
            end_time=400,
        )
        
        # Verify all differences are within window
        for diff in result["differences"]:
            assert 200 <= diff["time"] <= 400
