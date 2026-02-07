"""
Performance monitoring and statistics tools.

This module provides tools for monitoring server performance, memory usage,
cache effectiveness, and waveform file statistics.
"""

from typing import Dict, Any, Optional
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
import os
from datetime import datetime
from .session import SessionManager


async def perf_get_statistics(
    session_manager: SessionManager,
    session_id: str,
) -> Dict[str, Any]:
    """
    Get comprehensive statistics about a waveform file.
    
    Provides insights into file characteristics, signal density, and
    simulation complexity.
    
    Args:
        session_manager: Session management instance
        session_id: Active waveform session
        
    Returns:
        {
            "file_info": {
                "format": str,
                "path": str,
                "size_bytes": int,
                "size_mb": float
            },
            "time_info": {
                "start_time": int,
                "end_time": int,
                "duration": int,
                "time_points": int
            },
            "hierarchy_stats": {
                "total_scopes": int,
                "total_variables": int,
                "max_depth": int
            },
            "signal_stats": {
                "total_changes": int | None,
                "avg_changes_per_signal": float | None,
                "change_density": float | None
            }
        }
    """
    session = session_manager.get_session(session_id)
    waveform = session.waveform
    hierarchy = session.hierarchy
    time_table = session.time_table
    
    # File info
    file_path = session.file_path
    file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    
    # Time range
    start_time = time_table[0]
    end_time = start_time
    time_points = 0
    idx = 0
    try:
        while True:
            end_time = time_table[idx]
            time_points = idx + 1
            idx += 1
    except IndexError:
        pass
    
    duration = end_time - start_time
    
    # Hierarchy stats
    total_scopes = 0
    total_variables = 0
    
    def count_scopes_recursive(scope, depth=0):
        nonlocal total_scopes, total_variables
        total_scopes += 1
        
        # Count variables in this scope
        for var in scope.vars(hierarchy):
            total_variables += 1
        
        # Recurse into child scopes
        max_child_depth = depth
        for child_scope in scope.scopes(hierarchy):
            child_depth = count_scopes_recursive(child_scope, depth + 1)
            max_child_depth = max(max_child_depth, child_depth)
        
        return max_child_depth + 1
    
    max_depth = 0
    for top_scope in hierarchy.top_scopes():
        depth = count_scopes_recursive(top_scope, 0)
        max_depth = max(max_depth, depth)
    
    # Signal statistics (optional - can be expensive)
    # For now, return None to avoid performance issues
    total_changes = None
    avg_changes = None
    change_density = None
    
    return {
        "file_info": {
            "format": hierarchy.file_format(),
            "path": file_path,
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
        },
        "time_info": {
            "start_time": start_time,
            "end_time": end_time,
            "duration": duration,
            "time_points": time_points,
        },
        "hierarchy_stats": {
            "total_scopes": total_scopes,
            "total_variables": total_variables,
            "max_depth": max_depth,
        },
        "signal_stats": {
            "total_changes": total_changes,
            "avg_changes_per_signal": avg_changes,
            "change_density": change_density,
        }
    }


async def perf_memory_usage(
    session_manager: SessionManager,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get memory usage statistics for the server and sessions.
    
    Provides insights into memory consumption to help diagnose
    performance issues and optimize resource usage.
    
    Args:
        session_manager: Session management instance
        session_id: Optional specific session to examine (None = all sessions)
        
    Returns:
        {
            "process": {
                "pid": int,
                "memory_mb": float,
                "memory_percent": float,
                "cpu_percent": float
            },
            "sessions": {
                "total": int,
                "active": int,
                "session_list": [
                    {
                        "session_id": str,
                        "file_path": str,
                        "age_seconds": int,
                        "idle_seconds": int
                    },
                    ...
                ]
            },
            "cache": {
                "signal_cache_size": int,
                "signal_cache_max": int,
                "cache_utilization": float
            } | None
        }
    """
    # Check if psutil is available
    if not PSUTIL_AVAILABLE:
        return {
            "error": "psutil not available - install with: pip install psutil",
            "process": {
                "pid": os.getpid(),
                "memory_mb": None,
                "memory_percent": None,
                "cpu_percent": None
            },
            "sessions": {
                "total": len(session_manager.list_sessions()),
                "max": session_manager.max_sessions,
                "details": []
            },
            "cache": None
        }
    
    # Process-level stats
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    # Session stats
    session_ids = session_manager.list_sessions()
    now = datetime.now()
    
    session_list = []
    for session_id in session_ids:
        session = session_manager._sessions.get(session_id)
        if session:
            age = (now - session.created_at).total_seconds()
            idle = (now - session.last_accessed).total_seconds()
            
            session_list.append({
                "session_id": session_id,
                "file_path": session.file_path,
                "age_seconds": int(age),
                "idle_seconds": int(idle),
            })
    
    # Cache stats (if available)
    cache_info = None
    if session_id:
        # Would need access to SignalCache instance
        # For now, return None
        pass
    
    return {
        "process": {
            "pid": os.getpid(),
            "memory_mb": round(memory_info.rss / (1024 * 1024), 2),
            "memory_percent": round(process.memory_percent(), 2),
            "cpu_percent": round(process.cpu_percent(interval=0.1), 2),
        },
        "sessions": {
            "total": len(session_ids),
            "active": len(session_ids),
            "session_list": session_list,
        },
        "cache": cache_info,
    }


async def perf_cache_stats(
    signal_tools,
    session_id: str,
) -> Dict[str, Any]:
    """
    Get signal cache statistics for a session.
    
    Args:
        signal_tools: SignalTools instance with cache
        session_id: Active waveform session
        
    Returns:
        {
            "cache_size": int,
            "cache_max": int,
            "utilization": float,
            "cached_signals": List[str]
        }
    """
    cache = signal_tools.signal_cache
    
    # Get cached signals for this session
    cached_signals = []
    for key in cache._cache.keys():
        sid, path = key
        if sid == session_id:
            cached_signals.append(path)
    
    cache_size = len(cached_signals)
    
    return {
        "cache_size": cache_size,
        "cache_max": cache.max_size,
        "utilization": round(cache_size / cache.max_size, 2) if cache.max_size > 0 else 0.0,
        "cached_signals": cached_signals[:20],  # Return first 20
        "total_cached": cache_size,
    }
