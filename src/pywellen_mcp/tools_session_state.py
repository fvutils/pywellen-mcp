"""
Session state persistence and bookmarking tools.

This module provides tools for saving/loading session state and managing
bookmarks for long debugging sessions.
"""

from typing import Dict, Any, List, Optional
import json
from pathlib import Path
from datetime import datetime
from .session import SessionManager
from .errors import SessionError, FileError


async def session_save_state(
    session_manager: SessionManager,
    session_id: str,
    save_path: Optional[str] = None,
    include_bookmarks: bool = True,
    include_cache: bool = False,
) -> Dict[str, Any]:
    """
    Save session state to a file for later restoration.
    
    Useful for:
    - Preserving investigation state across sessions
    - Sharing debugging context with team members
    - Resuming long analysis workflows
    
    Args:
        session_manager: Session management instance
        session_id: Active waveform session to save
        save_path: Optional path to save state (default: session_<id>.json)
        include_bookmarks: Include bookmarks in saved state
        include_cache: Include cached signal list (not signal data)
        
    Returns:
        {
            "save_path": str,
            "session_id": str,
            "timestamp": str,
            "state_size_bytes": int
        }
    """
    session = session_manager.get_session(session_id)
    
    # Build state dictionary
    state = {
        "version": "1.0",
        "session_id": session_id,
        "saved_at": datetime.now().isoformat(),
        "file_path": session.file_path,
        "config": {
            "multi_threaded": session.multi_threaded,
            "remove_empty_scopes": session.remove_empty_scopes,
        },
        "bookmarks": session.bookmarks if include_bookmarks else [],
    }
    
    if include_cache:
        # Include list of cached signals (not the actual data)
        state["cached_signals"] = []  # Would need SignalCache integration
    
    # Determine save path
    if save_path is None:
        save_path = f"session_{session_id[:8]}.json"
    
    save_path = Path(save_path)
    
    # Write to file
    try:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        raise FileError(f"Failed to save session state: {e}", {"path": str(save_path)})
    
    # Get file size
    state_size = save_path.stat().st_size
    
    return {
        "save_path": str(save_path),
        "session_id": session_id,
        "timestamp": state["saved_at"],
        "state_size_bytes": state_size,
    }


async def session_load_state(
    session_manager: SessionManager,
    load_path: str,
    restore_bookmarks: bool = True,
) -> Dict[str, Any]:
    """
    Load session state from a previously saved file.
    
    Recreates a session with the same configuration and optionally
    restores bookmarks from the saved state.
    
    Args:
        session_manager: Session management instance
        load_path: Path to saved state file
        restore_bookmarks: Restore bookmarks from saved state
        
    Returns:
        {
            "session_id": str,
            "file_path": str,
            "original_session_id": str,
            "saved_at": str,
            "bookmarks_restored": int
        }
    """
    load_path = Path(load_path)
    
    # Read state file
    try:
        with open(load_path, 'r') as f:
            state = json.load(f)
    except Exception as e:
        raise FileError(f"Failed to load session state: {e}", {"path": str(load_path)})
    
    # Validate state version
    if state.get("version") != "1.0":
        raise SessionError(
            f"Unsupported state version: {state.get('version')}",
            {"supported_versions": ["1.0"]}
        )
    
    # Create new session with same file
    from .tools_waveform import WaveformTools
    waveform_tools = WaveformTools(session_manager)
    
    open_result = await waveform_tools.waveform_open(
        path=state["file_path"],
        multi_threaded=state["config"]["multi_threaded"],
        remove_empty_scopes=state["config"]["remove_empty_scopes"],
    )
    
    new_session_id = open_result["session_id"]
    
    # Restore bookmarks
    bookmarks_restored = 0
    if restore_bookmarks and "bookmarks" in state:
        session = session_manager.get_session(new_session_id)
        session.bookmarks = state["bookmarks"]
        bookmarks_restored = len(state["bookmarks"])
    
    return {
        "session_id": new_session_id,
        "file_path": state["file_path"],
        "original_session_id": state["session_id"],
        "saved_at": state["saved_at"],
        "bookmarks_restored": bookmarks_restored,
    }


async def session_add_bookmark(
    session_manager: SessionManager,
    session_id: str,
    time: int,
    label: str,
    notes: Optional[str] = None,
    signals: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Add a bookmark to mark an interesting time point.
    
    Bookmarks help organize investigation by marking important events,
    transitions, or areas of interest.
    
    Args:
        session_manager: Session management instance
        session_id: Active waveform session
        time: Simulation time to bookmark
        label: Short description/name for bookmark
        notes: Optional detailed notes
        signals: Optional list of related signal paths
        
    Returns:
        {
            "bookmark_id": int,
            "time": int,
            "label": str,
            "created_at": str
        }
    """
    session = session_manager.get_session(session_id)
    
    # Create bookmark
    bookmark = {
        "id": len(session.bookmarks),
        "time": time,
        "label": label,
        "notes": notes,
        "signals": signals or [],
        "created_at": datetime.now().isoformat(),
    }
    
    session.bookmarks.append(bookmark)
    
    return {
        "bookmark_id": bookmark["id"],
        "time": time,
        "label": label,
        "created_at": bookmark["created_at"],
    }


async def session_list_bookmarks(
    session_manager: SessionManager,
    session_id: str,
) -> Dict[str, Any]:
    """
    List all bookmarks for a session.
    
    Args:
        session_manager: Session management instance
        session_id: Active waveform session
        
    Returns:
        {
            "bookmarks": [
                {
                    "id": int,
                    "time": int,
                    "label": str,
                    "notes": str | None,
                    "signals": List[str],
                    "created_at": str
                },
                ...
            ],
            "count": int
        }
    """
    session = session_manager.get_session(session_id)
    
    return {
        "bookmarks": session.bookmarks,
        "count": len(session.bookmarks),
    }


async def session_remove_bookmark(
    session_manager: SessionManager,
    session_id: str,
    bookmark_id: int,
) -> Dict[str, Any]:
    """
    Remove a bookmark by ID.
    
    Args:
        session_manager: Session management instance
        session_id: Active waveform session
        bookmark_id: ID of bookmark to remove
        
    Returns:
        {
            "success": bool,
            "removed_id": int
        }
    """
    session = session_manager.get_session(session_id)
    
    # Find and remove bookmark
    original_len = len(session.bookmarks)
    session.bookmarks = [b for b in session.bookmarks if b["id"] != bookmark_id]
    
    removed = len(session.bookmarks) < original_len
    
    return {
        "success": removed,
        "removed_id": bookmark_id if removed else None,
    }
