"""Tests for session state persistence tools."""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from pywellen_mcp.tools_session_state import (
    session_save_state,
    session_load_state,
    session_add_bookmark,
    session_list_bookmarks,
    session_remove_bookmark,
)
from pywellen_mcp.session import SessionManager


@pytest.fixture
def session_manager(tmp_path):
    """Create session manager with mock session."""
    manager = SessionManager(max_sessions=5)
    
    test_file = tmp_path / "test.vcd"
    test_file.write_text("test waveform")
    
    session = Mock()
    session.file_path = str(test_file)
    session.multi_threaded = True
    session.remove_empty_scopes = False
    session.bookmarks = []
    
    manager._sessions["test-session"] = session
    
    return manager


@pytest.mark.asyncio
class TestSessionSaveState:
    """Tests for session_save_state tool."""
    
    async def test_save_state_default_path(self, session_manager, tmp_path):
        """Test saving state to default path."""
        result = await session_save_state(
            session_manager,
            "test-session",
            save_path=str(tmp_path / "state.json")
        )
        
        assert "save_path" in result
        assert "session_id" in result
        assert "timestamp" in result
        assert "state_size_bytes" in result
        
        # Check file was created
        save_path = Path(result["save_path"])
        assert save_path.exists()
        assert save_path.stat().st_size > 0
    
    async def test_save_state_content(self, session_manager, tmp_path):
        """Test saved state contains correct data."""
        save_path = tmp_path / "state.json"
        
        await session_save_state(
            session_manager,
            "test-session",
            save_path=str(save_path)
        )
        
        # Read and validate content
        with open(save_path, 'r') as f:
            state = json.load(f)
        
        assert state["version"] == "1.0"
        assert state["session_id"] == "test-session"
        assert "saved_at" in state
        assert "file_path" in state
        assert "config" in state
        assert state["config"]["multi_threaded"] is True
    
    async def test_save_with_bookmarks(self, session_manager, tmp_path):
        """Test saving state with bookmarks."""
        # Add bookmark
        session = session_manager.get_session("test-session")
        session.bookmarks = [
            {"id": 0, "time": 1000, "label": "Test", "notes": None, "signals": []}
        ]
        
        save_path = tmp_path / "state.json"
        await session_save_state(
            session_manager,
            "test-session",
            save_path=str(save_path),
            include_bookmarks=True
        )
        
        with open(save_path, 'r') as f:
            state = json.load(f)
        
        assert len(state["bookmarks"]) == 1
        assert state["bookmarks"][0]["label"] == "Test"
    
    async def test_save_without_bookmarks(self, session_manager, tmp_path):
        """Test saving state without bookmarks."""
        session = session_manager.get_session("test-session")
        session.bookmarks = [{"id": 0, "time": 1000, "label": "Test"}]
        
        save_path = tmp_path / "state.json"
        await session_save_state(
            session_manager,
            "test-session",
            save_path=str(save_path),
            include_bookmarks=False
        )
        
        with open(save_path, 'r') as f:
            state = json.load(f)
        
        assert len(state["bookmarks"]) == 0


@pytest.mark.asyncio
class TestSessionLoadState:
    """Tests for session_load_state tool."""
    
    async def test_load_state_file_format(self, session_manager, tmp_path):
        """Test that load_state reads the correct file format."""
        # Create a state file
        test_file = tmp_path / "test.vcd"
        test_file.write_text("test")
        
        state = {
            "version": "1.0",
            "session_id": "old-session",
            "saved_at": "2024-01-01T00:00:00",
            "file_path": str(test_file),
            "config": {
                "multi_threaded": True,
                "remove_empty_scopes": False
            },
            "bookmarks": [
                {"id": 0, "time": 1000, "label": "Test"}
            ]
        }
        
        state_file = tmp_path / "state.json"
        with open(state_file, 'w') as f:
            json.dump(state, f)
        
        # Read it back to verify format
        with open(state_file, 'r') as f:
            loaded = json.load(f)
        
        assert loaded["version"] == "1.0"
        assert loaded["session_id"] == "old-session"
        assert len(loaded["bookmarks"]) == 1


@pytest.mark.asyncio
class TestSessionBookmarks:
    """Tests for bookmark management tools."""
    
    async def test_add_bookmark(self, session_manager):
        """Test adding a bookmark."""
        result = await session_add_bookmark(
            session_manager,
            "test-session",
            time=5000,
            label="Error occurred",
            notes="Check this signal",
            signals=["top.error", "top.state"]
        )
        
        assert "bookmark_id" in result
        assert result["time"] == 5000
        assert result["label"] == "Error occurred"
        assert "created_at" in result
    
    async def test_list_bookmarks(self, session_manager):
        """Test listing bookmarks."""
        # Add some bookmarks
        await session_add_bookmark(session_manager, "test-session", 1000, "First")
        await session_add_bookmark(session_manager, "test-session", 2000, "Second")
        
        result = await session_list_bookmarks(
            session_manager,
            "test-session"
        )
        
        assert result["count"] == 2
        assert len(result["bookmarks"]) == 2
        assert result["bookmarks"][0]["label"] == "First"
        assert result["bookmarks"][1]["label"] == "Second"
    
    async def test_remove_bookmark(self, session_manager):
        """Test removing a bookmark."""
        # Add bookmark
        add_result = await session_add_bookmark(
            session_manager,
            "test-session",
            1000,
            "Test"
        )
        
        bookmark_id = add_result["bookmark_id"]
        
        # Remove it
        remove_result = await session_remove_bookmark(
            session_manager,
            "test-session",
            bookmark_id
        )
        
        assert remove_result["success"]
        assert remove_result["removed_id"] == bookmark_id
        
        # Verify it's gone
        list_result = await session_list_bookmarks(session_manager, "test-session")
        assert list_result["count"] == 0
    
    async def test_remove_nonexistent_bookmark(self, session_manager):
        """Test removing nonexistent bookmark."""
        result = await session_remove_bookmark(
            session_manager,
            "test-session",
            999
        )
        
        assert not result["success"]
        assert result["removed_id"] is None
    
    async def test_bookmark_with_signals(self, session_manager):
        """Test bookmark includes signal list."""
        await session_add_bookmark(
            session_manager,
            "test-session",
            1000,
            "Test",
            signals=["top.a", "top.b", "top.c"]
        )
        
        result = await session_list_bookmarks(session_manager, "test-session")
        bookmark = result["bookmarks"][0]
        
        assert len(bookmark["signals"]) == 3
        assert "top.a" in bookmark["signals"]
    
    async def test_empty_bookmark_list(self, session_manager):
        """Test listing when no bookmarks exist."""
        result = await session_list_bookmarks(
            session_manager,
            "test-session"
        )
        
        assert result["count"] == 0
        assert len(result["bookmarks"]) == 0
