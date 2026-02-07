"""Signal data access tools for querying waveform values."""

from typing import Any, Dict, List, Optional, Union
from collections import OrderedDict

from .session import SessionManager
from .errors import SessionError, QueryError, ErrorCode


class SignalCache:
    """LRU cache for signal data."""

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._cache: OrderedDict[tuple, Any] = OrderedDict()

    def get(self, session_id: str, var_path: str) -> Optional[Any]:
        """Get cached signal."""
        key = (session_id, var_path)
        if key in self._cache:
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def put(self, session_id: str, var_path: str, signal: Any) -> None:
        """Cache signal with LRU eviction."""
        key = (session_id, var_path)
        
        # If already exists, update and move to end
        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache[key] = signal
            return
        
        # If at capacity, remove oldest
        if len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)
        
        self._cache[key] = signal

    def clear_session(self, session_id: str) -> int:
        """Clear all cached signals for a session."""
        to_remove = [key for key in self._cache if key[0] == session_id]
        for key in to_remove:
            del self._cache[key]
        return len(to_remove)

    def clear(self) -> None:
        """Clear entire cache."""
        self._cache.clear()

    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)


class SignalTools:
    """Tools for accessing signal data."""

    def __init__(self, session_manager: SessionManager, cache_size: int = 100):
        self.session_manager = session_manager
        self.signal_cache = SignalCache(max_size=cache_size)

    async def signal_get_value(
        self,
        session_id: str,
        variable_path: str,
        times: Union[int, List[int]],
        format: str = "auto",
    ) -> Dict[str, Any]:
        """
        Query signal value(s) at specific time(s).

        Args:
            session_id: Session identifier
            variable_path: Full hierarchical path to variable
            times: Single time or list of times to query
            format: Output format - "auto", "int", "hex", "bin", "string"

        Returns:
            Dictionary with values at requested times
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            raise SessionError(
                f"Session not found: {session_id}",
                code=ErrorCode.SESSION_NOT_FOUND,
                context={"session_id": session_id},
            )

        # Convert single time to list
        time_list = [times] if isinstance(times, int) else times

        # Get or cache signal
        signal = self._get_signal(session, variable_path)

        # Query values
        values = []
        for time in time_list:
            try:
                value = signal.value_at_time(time)
                formatted_value = self._format_value(value, format)
                values.append({"time": time, "value": formatted_value})
            except Exception as e:
                # Signal may not have value at this time
                values.append({"time": time, "value": None, "error": str(e)})

        return {
            "session_id": session_id,
            "variable_path": variable_path,
            "format": format,
            "values": values,
            "count": len(values),
        }

    async def signal_get_changes(
        self,
        session_id: str,
        variable_path: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        max_changes: Optional[int] = None,
        format: str = "auto",
    ) -> Dict[str, Any]:
        """
        Get all value changes for a signal.

        Args:
            session_id: Session identifier
            variable_path: Full hierarchical path to variable
            start_time: Optional start time filter (inclusive)
            end_time: Optional end time filter (inclusive)
            max_changes: Optional limit on number of changes returned
            format: Output format - "auto", "int", "hex", "bin", "string"

        Returns:
            Dictionary with list of (time, value) changes
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            raise SessionError(
                f"Session not found: {session_id}",
                code=ErrorCode.SESSION_NOT_FOUND,
                context={"session_id": session_id},
            )

        # Validate time range
        if start_time is not None and end_time is not None and start_time > end_time:
            raise QueryError(
                f"Invalid time range: start_time ({start_time}) > end_time ({end_time})",
                code=ErrorCode.INVALID_TIME_RANGE,
                context={"start_time": start_time, "end_time": end_time},
            )

        # Get or cache signal
        signal = self._get_signal(session, variable_path)

        # Collect changes
        changes = []
        time_table = session.time_table
        
        try:
            for time_idx, value_str in signal.all_changes():
                # Convert index to actual time
                try:
                    actual_time = time_table[time_idx]
                except (IndexError, Exception):
                    # Time index out of range, skip
                    continue

                # Apply time filters
                if start_time is not None and actual_time < start_time:
                    continue
                if end_time is not None and actual_time > end_time:
                    continue

                # Format value
                formatted_value = self._format_value(value_str, format)
                changes.append({"time": actual_time, "value": formatted_value})

                # Check max changes limit
                if max_changes is not None and len(changes) >= max_changes:
                    break

        except Exception as e:
            raise QueryError(
                f"Failed to iterate signal changes: {e}",
                code=ErrorCode.INTERNAL_ERROR,
                context={"variable_path": variable_path, "error": str(e)},
            )

        return {
            "session_id": session_id,
            "variable_path": variable_path,
            "format": format,
            "changes": changes,
            "count": len(changes),
            "truncated": max_changes is not None and len(changes) >= max_changes,
            "time_range": {
                "start": start_time,
                "end": end_time,
            },
        }

    async def time_get_range(self, session_id: str) -> Dict[str, Any]:
        """
        Get simulation time range.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary with min time, max time, and number of time points
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            raise SessionError(
                f"Session not found: {session_id}",
                code=ErrorCode.SESSION_NOT_FOUND,
                context={"session_id": session_id},
            )

        time_table = session.time_table

        # Find time range by probing time_table
        try:
            min_time = time_table[0]
        except (IndexError, Exception):
            # Empty time table
            return {
                "session_id": session_id,
                "min_time": None,
                "max_time": None,
                "num_time_points": 0,
            }

        # Find max by iterating until we hit an error
        max_idx = 0
        max_time = min_time
        try:
            while True:
                time = time_table[max_idx]
                max_time = time
                max_idx += 1
        except (IndexError, Exception):
            # Reached end
            pass

        return {
            "session_id": session_id,
            "min_time": min_time,
            "max_time": max_time,
            "num_time_points": max_idx,
        }

    async def time_convert(
        self,
        session_id: str,
        indices: Optional[List[int]] = None,
        times: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Convert between time indices and actual times.

        Args:
            session_id: Session identifier
            indices: Optional list of time indices to convert to times
            times: Optional list of times to find nearest indices for

        Returns:
            Dictionary with conversion mappings
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            raise SessionError(
                f"Session not found: {session_id}",
                code=ErrorCode.SESSION_NOT_FOUND,
                context={"session_id": session_id},
            )

        if indices is None and times is None:
            raise QueryError(
                "Must provide either 'indices' or 'times'",
                code=ErrorCode.INVALID_PARAMETER,
                context={},
            )

        time_table = session.time_table
        result = {"session_id": session_id}

        # Convert indices to times
        if indices is not None:
            index_to_time = []
            for idx in indices:
                try:
                    time = time_table[idx]
                    index_to_time.append({"index": idx, "time": time})
                except (IndexError, Exception):
                    index_to_time.append({"index": idx, "time": None, "error": "Index out of range"})
            result["index_to_time"] = index_to_time

        # Convert times to nearest indices
        if times is not None:
            # Build time->index mapping by scanning time table
            time_to_index_map = {}
            idx = 0
            try:
                while True:
                    time = time_table[idx]
                    time_to_index_map[time] = idx
                    idx += 1
            except (IndexError, Exception):
                pass

            time_to_index = []
            for query_time in times:
                # Find exact match or closest time
                if query_time in time_to_index_map:
                    time_to_index.append({
                        "time": query_time,
                        "index": time_to_index_map[query_time],
                        "exact": True,
                    })
                else:
                    # Find nearest time
                    nearest_time = None
                    nearest_idx = None
                    min_diff = float('inf')
                    
                    for time, idx in time_to_index_map.items():
                        diff = abs(time - query_time)
                        if diff < min_diff:
                            min_diff = diff
                            nearest_time = time
                            nearest_idx = idx
                    
                    if nearest_time is not None:
                        time_to_index.append({
                            "time": query_time,
                            "index": nearest_idx,
                            "exact": False,
                            "nearest_time": nearest_time,
                        })
                    else:
                        time_to_index.append({
                            "time": query_time,
                            "index": None,
                            "error": "No time points available",
                        })
            
            result["time_to_index"] = time_to_index

        return result

    async def signal_get_statistics(
        self,
        session_id: str,
        variable_path: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Compute statistics on signal behavior.

        Args:
            session_id: Session identifier
            variable_path: Full hierarchical path to variable
            start_time: Optional start time filter
            end_time: Optional end time filter

        Returns:
            Dictionary with signal statistics
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            raise SessionError(
                f"Session not found: {session_id}",
                code=ErrorCode.SESSION_NOT_FOUND,
                context={"session_id": session_id},
            )

        # Get signal and changes
        changes_result = await self.signal_get_changes(
            session_id,
            variable_path,
            start_time=start_time,
            end_time=end_time,
            format="string",
        )

        changes = changes_result["changes"]
        
        if len(changes) == 0:
            return {
                "session_id": session_id,
                "variable_path": variable_path,
                "num_changes": 0,
                "message": "No changes in specified time range",
            }

        # Basic statistics
        num_changes = len(changes)
        first_change_time = changes[0]["time"]
        last_change_time = changes[-1]["time"]

        # Count unique values
        unique_values = set(c["value"] for c in changes if c["value"] is not None)

        stats = {
            "session_id": session_id,
            "variable_path": variable_path,
            "num_changes": num_changes,
            "num_unique_values": len(unique_values),
            "first_change_time": first_change_time,
            "last_change_time": last_change_time,
            "time_range": {
                "start": start_time,
                "end": end_time,
            },
        }

        # Try to compute numeric statistics if values are numeric
        try:
            numeric_values = []
            for change in changes:
                val = change["value"]
                if val is not None and val != "x" and val != "z":
                    # Try to parse as integer
                    if isinstance(val, int):
                        numeric_values.append(val)
                    elif isinstance(val, str):
                        # Try binary, hex, or decimal
                        if val.startswith("0x") or val.startswith("0X"):
                            numeric_values.append(int(val, 16))
                        elif val.startswith("0b") or val.startswith("0B"):
                            numeric_values.append(int(val, 2))
                        elif val.isdigit():
                            numeric_values.append(int(val))

            if numeric_values:
                stats["numeric_statistics"] = {
                    "min_value": min(numeric_values),
                    "max_value": max(numeric_values),
                    "num_numeric_samples": len(numeric_values),
                }
        except Exception:
            # Not numeric, skip numeric stats
            pass

        return stats

    def _get_signal(self, session, variable_path: str):
        """Get signal from cache or load from waveform."""
        # Check cache
        cached = self.signal_cache.get(session.session_id, variable_path)
        if cached is not None:
            return cached

        # Load signal
        try:
            signal = session.waveform.get_signal_from_path(variable_path)
            
            # Cache it
            self.signal_cache.put(session.session_id, variable_path, signal)
            
            return signal
        except Exception as e:
            raise QueryError(
                f"Signal not found: {variable_path}",
                code=ErrorCode.SIGNAL_NOT_FOUND,
                context={"variable_path": variable_path, "error": str(e)},
            )

    def _format_value(self, value: Union[int, str, None], format: str) -> Union[int, str, None]:
        """Format signal value according to requested format."""
        if value is None:
            return None

        if format == "auto":
            return value

        # Convert to string first
        value_str = str(value) if not isinstance(value, str) else value

        if format == "string":
            return value_str

        # Try to parse as integer for formatting
        try:
            if isinstance(value, int):
                int_val = value
            elif value_str.startswith("0x") or value_str.startswith("0X"):
                int_val = int(value_str, 16)
            elif value_str.startswith("0b") or value_str.startswith("0B"):
                int_val = int(value_str, 2)
            elif value_str.isdigit():
                int_val = int(value_str)
            else:
                # Can't parse, return as string
                return value_str

            # Apply formatting
            if format == "int":
                return int_val
            elif format == "hex":
                return hex(int_val)
            elif format == "bin":
                return bin(int_val)
            else:
                return value_str

        except (ValueError, TypeError):
            # Can't format, return as-is
            return value_str
