"""Tests for performance monitoring tools."""

import pytest
import os
from unittest.mock import Mock, patch
from pywellen_mcp.tools_performance import (
    perf_get_statistics,
    perf_memory_usage,
    perf_cache_stats,
)
from pywellen_mcp.session import SessionManager
from pywellen_mcp.tools_signal import SignalTools


@pytest.fixture
def mock_hierarchy():
    """Create mock hierarchy."""
    top_scope = Mock()
    top_scope.vars = Mock(return_value=iter([Mock(), Mock(), Mock()]))
    top_scope.scopes = Mock(return_value=iter([]))
    
    child_scope = Mock()
    child_scope.vars = Mock(return_value=iter([Mock(), Mock()]))
    child_scope.scopes = Mock(return_value=iter([]))
    
    hierarchy = Mock()
    hierarchy.file_format = Mock(return_value="VCD")
    hierarchy.top_scopes = Mock(return_value=iter([top_scope, child_scope]))
    
    return hierarchy


@pytest.fixture
def session_manager(tmp_path, mock_hierarchy):
    """Create session manager with mock session."""
    from datetime import datetime
    manager = SessionManager(max_sessions=5)
    
    # Create a temp file for file size testing
    test_file = tmp_path / "test.vcd"
    test_file.write_text("test waveform data" * 1000)
    
    session = Mock()
    session.waveform = Mock()
    session.hierarchy = mock_hierarchy
    session.file_path = str(test_file)
    session.bookmarks = []
    session.created_at = datetime.now()
    session.last_accessed = datetime.now()
    
    time_table = Mock()
    def time_table_getitem(self, idx):
        if idx > 10:
            raise IndexError("Out of range")
        return idx * 1000
    time_table.__getitem__ = time_table_getitem
    session.time_table = time_table
    
    manager._sessions["test-session"] = session
    
    return manager


@pytest.fixture
def signal_tools(session_manager):
    """Create signal tools instance."""
    return SignalTools(session_manager)


@pytest.mark.asyncio
class TestPerfGetStatistics:
    """Tests for perf_get_statistics tool."""
    
    async def test_get_statistics(self, session_manager):
        """Test getting waveform statistics."""
        result = await perf_get_statistics(
            session_manager,
            "test-session"
        )
        
        assert "file_info" in result
        assert "time_info" in result
        assert "hierarchy_stats" in result
        assert "signal_stats" in result
        
        # File info
        assert result["file_info"]["format"] == "VCD"
        assert "size_bytes" in result["file_info"]
        assert "size_mb" in result["file_info"]
        
        # Time info
        assert result["time_info"]["start_time"] == 0
        assert result["time_info"]["end_time"] == 10000
        assert result["time_info"]["duration"] == 10000
        assert result["time_info"]["time_points"] == 11
        
        # Hierarchy stats
        assert result["hierarchy_stats"]["total_scopes"] == 2
        assert result["hierarchy_stats"]["total_variables"] == 5
        assert result["hierarchy_stats"]["max_depth"] > 0
    
    async def test_file_size_calculation(self, session_manager):
        """Test file size is calculated correctly."""
        result = await perf_get_statistics(
            session_manager,
            "test-session"
        )
        
        size_bytes = result["file_info"]["size_bytes"]
        size_mb = result["file_info"]["size_mb"]
        
        assert size_bytes > 0
        assert size_mb == round(size_bytes / (1024 * 1024), 2)


@pytest.mark.asyncio
class TestPerfMemoryUsage:
    """Tests for perf_memory_usage tool."""
    
    async def test_get_memory_usage(self, session_manager):
        """Test getting memory usage statistics."""
        result = await perf_memory_usage(
            session_manager,
            session_id=None
        )
        
        assert "process" in result
        assert "sessions" in result
        
        # Process stats
        assert result["process"]["pid"] == os.getpid()
        assert result["process"]["memory_mb"] > 0
        assert result["process"]["memory_percent"] >= 0
        assert result["process"]["cpu_percent"] >= 0
        
        # Session stats
        assert result["sessions"]["total"] >= 0
        assert result["sessions"]["active"] >= 0
        assert isinstance(result["sessions"]["session_list"], list)
    
    async def test_session_list_details(self, session_manager):
        """Test session list includes details."""
        result = await perf_memory_usage(
            session_manager,
            session_id=None
        )
        
        # Should have at least one session
        assert len(result["sessions"]["session_list"]) >= 1
        
        session_info = result["sessions"]["session_list"][0]
        assert "session_id" in session_info
        assert "file_path" in session_info
        assert "age_seconds" in session_info
        assert "idle_seconds" in session_info


@pytest.mark.asyncio
class TestPerfCacheStats:
    """Tests for perf_cache_stats tool."""
    
    async def test_get_cache_stats(self, signal_tools):
        """Test getting cache statistics."""
        # Add some items to cache
        signal_tools.signal_cache.put("test-session", "top.clk", Mock())
        signal_tools.signal_cache.put("test-session", "top.data", Mock())
        
        result = await perf_cache_stats(
            signal_tools,
            "test-session"
        )
        
        assert "cache_size" in result
        assert "cache_max" in result
        assert "utilization" in result
        assert "cached_signals" in result
        assert "total_cached" in result
        
        assert result["cache_size"] == 2
        assert result["total_cached"] == 2
        assert len(result["cached_signals"]) == 2
    
    async def test_cache_utilization(self, signal_tools):
        """Test cache utilization calculation."""
        # Fill cache partially
        cache = signal_tools.signal_cache
        for i in range(10):
            cache.put("test-session", f"signal_{i}", Mock())
        
        result = await perf_cache_stats(
            signal_tools,
            "test-session"
        )
        
        expected_utilization = round(10 / cache.max_size, 2)
        assert result["utilization"] == expected_utilization
    
    async def test_empty_cache(self, signal_tools):
        """Test stats for empty cache."""
        result = await perf_cache_stats(
            signal_tools,
            "test-session"
        )
        
        assert result["cache_size"] == 0
        assert result["utilization"] == 0.0
        assert len(result["cached_signals"]) == 0
    
    async def test_cache_limit_display(self, signal_tools):
        """Test that cached signals list is limited."""
        # Add more than 20 signals
        cache = signal_tools.signal_cache
        for i in range(30):
            cache.put("test-session", f"signal_{i}", Mock())
        
        result = await perf_cache_stats(
            signal_tools,
            "test-session"
        )
        
        # Should limit display to 20
        assert len(result["cached_signals"]) <= 20
        # But total should be accurate
        assert result["total_cached"] == 30
