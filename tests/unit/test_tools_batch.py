"""Tests for batch query operations."""

import pytest
from unittest.mock import Mock
from pywellen_mcp.tools_batch import batch_query_signals
from pywellen_mcp.session import SessionManager
from pywellen_mcp.tools_signal import SignalTools


class MockSignal:
    """Mock signal with predefined changes."""
    
    def __init__(self, changes):
        self._changes = changes
    
    def all_changes(self):
        return iter(self._changes)
    
    def value_at_time(self, time):
        result = None
        for time_idx, value in self._changes:
            if time_idx * 100 <= time:
                result = value
            else:
                break
        return result


class MockWaveform:
    """Mock waveform."""
    
    def __init__(self):
        self.signals = {
            "top.clk": MockSignal([(0, "0"), (1, "1"), (2, "0")]),
            "top.data": MockSignal([(0, "0xAA"), (2, "0xBB")]),
            "top.enable": MockSignal([(0, "0"), (1, "1")]),
        }
    
    def get_signal_from_path(self, path):
        if path in self.signals:
            return self.signals[path]
        raise ValueError(f"Signal not found: {path}")


@pytest.fixture
def session_manager():
    """Create session manager with mock session."""
    manager = SessionManager(max_sessions=5)
    
    session = Mock()
    session.waveform = MockWaveform()
    session.hierarchy = Mock()
    
    time_table = Mock()
    def time_table_getitem(self, idx):
        if idx > 10:
            raise IndexError("Out of range")
        return idx * 100
    time_table.__getitem__ = time_table_getitem
    session.time_table = time_table
    
    manager._sessions["test-session"] = session
    
    return manager


@pytest.fixture
def signal_tools(session_manager):
    """Create signal tools instance."""
    return SignalTools(session_manager)


@pytest.mark.asyncio
class TestBatchQuerySignals:
    """Tests for batch_query_signals tool."""
    
    async def test_single_query(self, session_manager, signal_tools):
        """Test batch with single query."""
        result = await batch_query_signals(
            session_manager,
            "test-session",
            queries=[
                {
                    "variable_path": "top.clk",
                    "operation": "get_value",
                    "params": {"times": 100}
                }
            ],
            signal_tools=signal_tools
        )
        
        assert result["total"] == 1
        assert result["successful"] == 1
        assert result["failed"] == 0
        assert result["results"][0]["success"]
        assert result["results"][0]["data"] is not None
    
    async def test_multiple_queries(self, session_manager, signal_tools):
        """Test batch with multiple queries."""
        result = await batch_query_signals(
            session_manager,
            "test-session",
            queries=[
                {
                    "variable_path": "top.clk",
                    "operation": "get_value",
                    "params": {"times": 100}
                },
                {
                    "variable_path": "top.data",
                    "operation": "get_changes",
                    "params": {}
                },
                {
                    "variable_path": "top.enable",
                    "operation": "get_statistics",
                    "params": {}
                }
            ],
            signal_tools=signal_tools
        )
        
        assert result["total"] == 3
        assert result["successful"] == 3
        assert result["failed"] == 0
        
        # All should succeed
        for res in result["results"]:
            assert res["success"]
            assert res["data"] is not None
    
    async def test_mixed_success_failure(self, session_manager, signal_tools):
        """Test batch with some failures."""
        result = await batch_query_signals(
            session_manager,
            "test-session",
            queries=[
                {
                    "variable_path": "top.clk",
                    "operation": "get_value",
                    "params": {"times": 100}
                },
                {
                    "variable_path": "top.nonexistent",
                    "operation": "get_value",
                    "params": {"times": 100}
                },
                {
                    "variable_path": "top.data",
                    "operation": "get_changes",
                    "params": {}
                }
            ],
            signal_tools=signal_tools
        )
        
        assert result["total"] == 3
        assert result["successful"] == 2
        assert result["failed"] == 1
        
        # Check individual results
        assert result["results"][0]["success"]
        assert not result["results"][1]["success"]
        assert result["results"][1]["error"] is not None
        assert result["results"][2]["success"]
    
    async def test_missing_variable_path(self, session_manager, signal_tools):
        """Test error when variable_path missing."""
        result = await batch_query_signals(
            session_manager,
            "test-session",
            queries=[
                {
                    "operation": "get_value",
                    "params": {"times": 100}
                }
            ],
            signal_tools=signal_tools
        )
        
        assert result["failed"] == 1
        assert not result["results"][0]["success"]
        assert "variable_path" in result["results"][0]["error"]
    
    async def test_missing_operation(self, session_manager, signal_tools):
        """Test error when operation missing."""
        result = await batch_query_signals(
            session_manager,
            "test-session",
            queries=[
                {
                    "variable_path": "top.clk",
                    "params": {"times": 100}
                }
            ],
            signal_tools=signal_tools
        )
        
        assert result["failed"] == 1
        assert not result["results"][0]["success"]
        assert "operation" in result["results"][0]["error"]
    
    async def test_invalid_operation(self, session_manager, signal_tools):
        """Test error for invalid operation."""
        result = await batch_query_signals(
            session_manager,
            "test-session",
            queries=[
                {
                    "variable_path": "top.clk",
                    "operation": "invalid_op",
                    "params": {}
                }
            ],
            signal_tools=signal_tools
        )
        
        assert result["failed"] == 1
        assert not result["results"][0]["success"]
    
    async def test_empty_batch(self, session_manager, signal_tools):
        """Test empty batch."""
        result = await batch_query_signals(
            session_manager,
            "test-session",
            queries=[],
            signal_tools=signal_tools
        )
        
        assert result["total"] == 0
        assert result["successful"] == 0
        assert result["failed"] == 0
    
    async def test_query_index_preserved(self, session_manager, signal_tools):
        """Test that query indices are preserved in results."""
        result = await batch_query_signals(
            session_manager,
            "test-session",
            queries=[
                {"variable_path": "top.clk", "operation": "get_value", "params": {"times": 100}},
                {"variable_path": "top.data", "operation": "get_value", "params": {"times": 200}},
                {"variable_path": "top.enable", "operation": "get_value", "params": {"times": 100}},
            ],
            signal_tools=signal_tools
        )
        
        # Check indices match
        for idx, res in enumerate(result["results"]):
            assert res["query_index"] == idx
