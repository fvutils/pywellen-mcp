"""
Debugging and analysis tools for waveform investigation.

This module provides tools for common hardware debugging workflows including
finding signal transitions, tracing causality, building event timelines, and
analyzing signal activity.
"""

from typing import List, Dict, Any, Optional, Literal, Tuple
from .session import SessionManager
from .errors import QueryError, SessionError


async def debug_find_transition(
    session_manager: SessionManager,
    session_id: str,
    variable_path: str,
    condition: Literal["equals", "not_equals", "greater", "less", "rises", "falls"],
    value: Optional[str] = None,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    max_results: int = 100,
) -> Dict[str, Any]:
    """
    Find transitions where a signal meets specific conditions.
    
    This tool is essential for debugging workflows like:
    - Finding when a state machine enters error state
    - Locating rising/falling edges of control signals
    - Finding when a counter reaches threshold
    
    Args:
        session_manager: Session management instance
        session_id: Active waveform session
        variable_path: Dot-separated signal path
        condition: Type of transition to find
            - "equals": Signal value equals target
            - "not_equals": Signal value changes from target
            - "greater": Signal becomes greater than target
            - "less": Signal becomes less than target
            - "rises": Signal transitions from 0 to 1 (1-bit only)
            - "falls": Signal transitions from 1 to 0 (1-bit only)
        value: Target value for comparison (not used for rises/falls)
        start_time: Start of search window
        end_time: End of search window
        max_results: Maximum transitions to return
        
    Returns:
        {
            "transitions": [
                {"time": int, "index": int, "value": str, "prev_value": str},
                ...
            ],
            "count": int,
            "truncated": bool
        }
    """
    session = session_manager.get_session(session_id)
    waveform = session.waveform
    hierarchy = session.hierarchy
    
    # Get signal
    try:
        signal = waveform.get_signal_from_path(variable_path)
    except Exception as e:
        raise QueryError(
            f"Failed to get signal '{variable_path}': {e}",
            {"session_id": session_id, "path": variable_path}
        )
    
    time_table = session.time_table
    
    # Determine time range
    if start_time is None:
        start_time = time_table[0]
    if end_time is None:
        # Find last valid index
        idx = 0
        try:
            while True:
                end_time = time_table[idx]
                idx += 1
        except IndexError:
            pass
    
    # Validate condition requirements
    if condition in ["equals", "not_equals", "greater", "less"] and value is None:
        raise QueryError(
            f"Condition '{condition}' requires 'value' parameter",
            {"condition": condition}
        )
    
    if condition in ["rises", "falls"] and value is not None:
        raise QueryError(
            f"Condition '{condition}' does not use 'value' parameter",
            {"condition": condition}
        )
    
    # Collect transitions
    transitions = []
    prev_value = None
    
    for time_idx, current_value in signal.all_changes():
        time = time_table[time_idx]
        
        # Skip if outside time window
        if time < start_time:
            prev_value = current_value
            continue
        if time > end_time:
            break
        
        # Check condition
        matches = False
        
        if condition == "equals":
            matches = str(current_value) == str(value)
        elif condition == "not_equals":
            matches = prev_value is not None and str(prev_value) == str(value) and str(current_value) != str(value)
        elif condition == "rises":
            matches = prev_value == "0" and current_value == "1"
        elif condition == "falls":
            matches = prev_value == "1" and current_value == "0"
        elif condition in ["greater", "less"]:
            # Try numeric comparison
            try:
                curr_num = int(str(current_value), 0) if isinstance(current_value, str) else current_value
                target_num = int(str(value), 0) if isinstance(value, str) else value
                
                if condition == "greater":
                    matches = curr_num > target_num and (prev_value is None or int(str(prev_value), 0) <= target_num)
                else:  # less
                    matches = curr_num < target_num and (prev_value is None or int(str(prev_value), 0) >= target_num)
            except (ValueError, TypeError):
                # Non-numeric values, skip
                pass
        
        if matches:
            transitions.append({
                "time": time,
                "index": time_idx,
                "value": str(current_value),
                "prev_value": str(prev_value) if prev_value is not None else None,
            })
            
            if len(transitions) >= max_results:
                break
        
        prev_value = current_value
    
    return {
        "transitions": transitions,
        "count": len(transitions),
        "truncated": len(transitions) >= max_results,
    }


async def debug_trace_causality(
    session_manager: SessionManager,
    session_id: str,
    target_path: str,
    target_time: int,
    search_window: int = 1000,
    related_signals: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Trace potential causes of a signal change.
    
    Find signals that changed shortly before a target signal transition,
    helping identify root causes in debugging.
    
    Args:
        session_manager: Session management instance
        session_id: Active waveform session
        target_path: Signal that changed
        target_time: Time of the target transition
        search_window: Time before target_time to search (in time units)
        related_signals: Optional list of signals to examine (None = all in same scope)
        
    Returns:
        {
            "target": {"path": str, "time": int, "value": str},
            "potential_causes": [
                {
                    "path": str,
                    "time": int,
                    "value": str,
                    "delta_time": int,
                    "relevance": float  # 0-1 score based on timing
                },
                ...
            ]
        }
    """
    session = session_manager.get_session(session_id)
    waveform = session.waveform
    hierarchy = session.hierarchy
    time_table = session.time_table
    
    # Get target signal's value at target time
    try:
        target_signal = waveform.get_signal_from_path(target_path)
        target_value = target_signal.value_at_time(target_time)
    except Exception as e:
        raise QueryError(
            f"Failed to get target signal: {e}",
            {"path": target_path, "time": target_time}
        )
    
    # Determine which signals to examine
    if related_signals is None:
        # Get all signals in same scope
        # Extract scope path (everything before last dot)
        parts = target_path.split(".")
        if len(parts) > 1:
            scope_path = ".".join(parts[:-1])
            # Find scope and get all its variables
            related_signals = []
            try:
                from .tools_hierarchy import _find_scope_by_path
                scope = _find_scope_by_path(hierarchy, scope_path)
                if scope:
                    for var in scope.vars(hierarchy):
                        full_path = var.full_name(hierarchy)
                        if full_path != target_path:
                            related_signals.append(full_path)
            except:
                pass
        
        if not related_signals:
            related_signals = []
    
    # Find changes in related signals before target time
    potential_causes = []
    search_start = max(0, target_time - search_window)
    
    for signal_path in related_signals[:50]:  # Limit to 50 signals for performance
        try:
            signal = waveform.get_signal_from_path(signal_path)
            
            # Find last change before target time
            last_change_time = None
            last_change_value = None
            
            for time_idx, value in signal.all_changes():
                time = time_table[time_idx]
                
                if time >= target_time:
                    break
                
                if time >= search_start:
                    last_change_time = time
                    last_change_value = value
            
            if last_change_time is not None:
                delta = target_time - last_change_time
                # Relevance score: closer in time = more relevant
                relevance = 1.0 - (delta / search_window)
                
                potential_causes.append({
                    "path": signal_path,
                    "time": last_change_time,
                    "value": str(last_change_value),
                    "delta_time": delta,
                    "relevance": round(relevance, 3),
                })
        except:
            # Skip signals that can't be loaded
            continue
    
    # Sort by relevance (most relevant first)
    potential_causes.sort(key=lambda x: x["relevance"], reverse=True)
    
    return {
        "target": {
            "path": target_path,
            "time": target_time,
            "value": str(target_value),
        },
        "potential_causes": potential_causes[:20],  # Return top 20
    }


async def debug_event_timeline(
    session_manager: SessionManager,
    session_id: str,
    signal_paths: List[str],
    start_time: int,
    end_time: int,
    max_events: int = 1000,
) -> Dict[str, Any]:
    """
    Build chronological timeline of events across multiple signals.
    
    Creates a unified view of when signals change, useful for understanding
    sequence of operations and signal interactions.
    
    Args:
        session_manager: Session management instance
        session_id: Active waveform session
        signal_paths: List of signals to include in timeline
        start_time: Timeline start
        end_time: Timeline end
        max_events: Maximum events to return
        
    Returns:
        {
            "events": [
                {
                    "time": int,
                    "signal": str,
                    "value": str,
                    "prev_value": str
                },
                ...
            ],
            "count": int,
            "truncated": bool
        }
    """
    session = session_manager.get_session(session_id)
    waveform = session.waveform
    time_table = session.time_table
    
    # Collect all events from all signals
    events = []
    
    for signal_path in signal_paths:
        try:
            signal = waveform.get_signal_from_path(signal_path)
            prev_value = None
            
            for time_idx, value in signal.all_changes():
                time = time_table[time_idx]
                
                if time < start_time:
                    prev_value = value
                    continue
                if time > end_time:
                    break
                
                events.append({
                    "time": time,
                    "signal": signal_path,
                    "value": str(value),
                    "prev_value": str(prev_value) if prev_value is not None else None,
                })
                
                prev_value = value
        except:
            # Skip signals that can't be loaded
            continue
    
    # Sort by time
    events.sort(key=lambda x: x["time"])
    
    # Limit results
    truncated = len(events) > max_events
    events = events[:max_events]
    
    return {
        "events": events,
        "count": len(events),
        "truncated": truncated,
    }


async def search_by_activity(
    session_manager: SessionManager,
    session_id: str,
    scope_path: Optional[str] = None,
    min_toggles: Optional[int] = None,
    max_toggles: Optional[int] = None,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """
    Find signals by their toggle activity/change frequency.
    
    Useful for:
    - Finding clock signals (high toggle rate)
    - Finding static/constant signals (zero toggles)
    - Identifying active state machines
    - Filtering noisy signals
    
    Args:
        session_manager: Session management instance
        session_id: Active waveform session
        scope_path: Limit search to specific scope (None = all signals)
        min_toggles: Minimum number of transitions
        max_toggles: Maximum number of transitions
        start_time: Start of analysis window
        end_time: End of analysis window
        limit: Maximum results to return
        
    Returns:
        {
            "signals": [
                {
                    "path": str,
                    "toggle_count": int,
                    "toggle_rate": float,  # toggles per time unit
                    "time_span": int
                },
                ...
            ],
            "count": int
        }
    """
    session = session_manager.get_session(session_id)
    waveform = session.waveform
    hierarchy = session.hierarchy
    time_table = session.time_table
    
    # Determine time range
    if start_time is None:
        start_time = time_table[0]
    if end_time is None:
        idx = 0
        try:
            while True:
                end_time = time_table[idx]
                idx += 1
        except IndexError:
            pass
    
    time_span = end_time - start_time
    
    # Get signals to analyze
    if scope_path:
        from .tools_hierarchy import _find_scope_by_path
        scope = _find_scope_by_path(hierarchy, scope_path)
        if not scope:
            raise QueryError(
                f"Scope not found: {scope_path}",
                {"scope_path": scope_path}
            )
        variables = list(scope.vars(hierarchy))
    else:
        variables = list(hierarchy.all_vars())
    
    # Analyze each signal
    results = []
    
    for var in variables[:1000]:  # Limit to 1000 signals for performance
        try:
            signal = waveform.get_signal(var)
            toggle_count = 0
            
            for time_idx, value in signal.all_changes():
                time = time_table[time_idx]
                if start_time <= time <= end_time:
                    toggle_count += 1
            
            # Apply filters
            if min_toggles is not None and toggle_count < min_toggles:
                continue
            if max_toggles is not None and toggle_count > max_toggles:
                continue
            
            toggle_rate = toggle_count / time_span if time_span > 0 else 0
            
            results.append({
                "path": var.full_name(hierarchy),
                "toggle_count": toggle_count,
                "toggle_rate": round(toggle_rate, 6),
                "time_span": time_span,
            })
        except:
            continue
    
    # Sort by toggle count (descending)
    results.sort(key=lambda x: x["toggle_count"], reverse=True)
    results = results[:limit]
    
    return {
        "signals": results,
        "count": len(results),
    }


async def signal_compare(
    session_manager: SessionManager,
    session_id: str,
    signal_path1: str,
    signal_path2: str,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Compare two signals and find differences.
    
    Useful for:
    - Comparing expected vs actual signals
    - Checking redundant signals match
    - Finding divergence points
    
    Args:
        session_manager: Session management instance
        session_id: Active waveform session
        signal_path1: First signal path
        signal_path2: Second signal path
        start_time: Start of comparison window
        end_time: End of comparison window
        
    Returns:
        {
            "signal1": str,
            "signal2": str,
            "differences": [
                {"time": int, "value1": str, "value2": str},
                ...
            ],
            "difference_count": int,
            "first_difference_time": int | None,
            "match_percentage": float
        }
    """
    session = session_manager.get_session(session_id)
    waveform = session.waveform
    time_table = session.time_table
    
    # Get both signals
    try:
        signal1 = waveform.get_signal_from_path(signal_path1)
        signal2 = waveform.get_signal_from_path(signal_path2)
    except Exception as e:
        raise QueryError(
            f"Failed to get signals: {e}",
            {"signal1": signal_path1, "signal2": signal_path2}
        )
    
    # Determine time range
    if start_time is None:
        start_time = time_table[0]
    if end_time is None:
        idx = 0
        try:
            while True:
                end_time = time_table[idx]
                idx += 1
        except IndexError:
            pass
    
    # Build value maps for both signals
    def build_value_map(signal):
        value_map = {}
        for time_idx, value in signal.all_changes():
            time = time_table[time_idx]
            if start_time <= time <= end_time:
                value_map[time] = str(value)
        return value_map
    
    values1 = build_value_map(signal1)
    values2 = build_value_map(signal2)
    
    # Get all unique times where either signal changes
    all_times = sorted(set(values1.keys()) | set(values2.keys()))
    
    # Compare values at each time
    differences = []
    current_value1 = None
    current_value2 = None
    sample_count = 0
    match_count = 0
    first_difference_time = None
    
    for time in all_times:
        # Update current values
        if time in values1:
            current_value1 = values1[time]
        if time in values2:
            current_value2 = values2[time]
        
        if current_value1 is not None and current_value2 is not None:
            sample_count += 1
            if current_value1 == current_value2:
                match_count += 1
            else:
                if first_difference_time is None:
                    first_difference_time = time
                differences.append({
                    "time": time,
                    "value1": current_value1,
                    "value2": current_value2,
                })
    
    match_percentage = (match_count / sample_count * 100) if sample_count > 0 else 100.0
    
    return {
        "signal1": signal_path1,
        "signal2": signal_path2,
        "differences": differences[:100],  # Limit to first 100 differences
        "difference_count": len(differences),
        "first_difference_time": first_difference_time,
        "match_percentage": round(match_percentage, 2),
    }
