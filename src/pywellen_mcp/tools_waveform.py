"""Waveform management tools - open, close, query metadata."""

from typing import Any, Dict, Optional
from pathlib import Path

from .session import SessionManager, WaveformSession
from .errors import FileError, SessionError, ErrorCode


class WaveformTools:
    """Tools for waveform file management."""

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager

    async def waveform_open(
        self,
        path: str,
        multi_threaded: bool = True,
        remove_empty_scopes: bool = False,
    ) -> Dict[str, Any]:
        """
        Load a waveform file and create a session.

        Args:
            path: Path to waveform file (VCD/FST/GHW)
            multi_threaded: Enable parallel parsing (default: True)
            remove_empty_scopes: Remove scopes with empty names (default: False)

        Returns:
            Dictionary with session_id and file metadata
        """
        try:
            # Validate path
            filepath = Path(path)
            if not filepath.exists():
                raise FileError(
                    f"File not found: {path}",
                    code=ErrorCode.FILE_NOT_FOUND,
                    context={"path": path},
                )

            if not filepath.is_file():
                raise FileError(
                    f"Path is not a file: {path}",
                    code=ErrorCode.INVALID_PARAMETER,
                    context={"path": path},
                )

            # Create session
            session = self.session_manager.create_session(
                filepath=str(filepath),
                multi_threaded=multi_threaded,
                remove_scopes_with_empty_name=remove_empty_scopes,
            )

            # Get file format and metadata
            hierarchy = session.hierarchy
            file_format = hierarchy.file_format()

            # Count variables
            var_count = sum(1 for _ in hierarchy.all_vars())

            # Get time range
            time_table = session.time_table
            try:
                min_time = time_table[0]
                # Find max time by iterating (no length method)
                max_idx = 0
                try:
                    while True:
                        time_table[max_idx]
                        max_idx += 1
                except (IndexError, Exception):
                    max_idx = max(0, max_idx - 1)
                max_time = time_table[max_idx] if max_idx >= 0 else min_time
            except (IndexError, Exception):
                min_time = 0
                max_time = 0

            result = {
                "session_id": session.session_id,
                "format": file_format,
                "path": str(filepath.absolute()),
                "num_variables": var_count,
                "time_range": {"min": min_time, "max": max_time},
            }

            # Add optional metadata if available
            timescale = hierarchy.timescale()
            if timescale:
                result["timescale"] = {
                    "factor": timescale.factor,
                    "unit": str(timescale.unit),
                }

            date = hierarchy.date()
            if date:
                result["date"] = date

            version = hierarchy.version()
            if version:
                result["version"] = version

            return result

        except FileNotFoundError as e:
            raise FileError(
                str(e),
                code=ErrorCode.FILE_NOT_FOUND,
                context={"path": path},
            )
        except RuntimeError as e:
            error_msg = str(e)
            if "Maximum number of sessions" in error_msg:
                raise SessionError(
                    error_msg,
                    code=ErrorCode.SESSION_LIMIT_EXCEEDED,
                    context={"max_sessions": self.session_manager.max_sessions},
                )
            else:
                raise FileError(
                    f"Failed to load waveform: {error_msg}",
                    code=ErrorCode.FILE_CORRUPTED,
                    context={"path": path, "error": error_msg},
                )

    async def waveform_info(self, session_id: str) -> Dict[str, Any]:
        """
        Get metadata about a loaded waveform.

        Args:
            session_id: Session identifier from waveform_open

        Returns:
            Dictionary with file metadata
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            raise SessionError(
                f"Session not found: {session_id}",
                code=ErrorCode.SESSION_NOT_FOUND,
                context={"session_id": session_id},
            )

        hierarchy = session.hierarchy

        # Get basic info
        result = {
            "session_id": session_id,
            "format": hierarchy.file_format(),
            "path": str(session.filepath.absolute()),
            "created_at": session.created_at.isoformat(),
            "last_accessed": session.last_accessed.isoformat(),
        }

        # Add optional metadata
        timescale = hierarchy.timescale()
        if timescale:
            result["timescale"] = {
                "factor": timescale.factor,
                "unit": str(timescale.unit),
            }

        date = hierarchy.date()
        if date:
            result["date"] = date

        version = hierarchy.version()
        if version:
            result["version"] = version

        # Count scopes and variables
        scope_count = sum(1 for _ in hierarchy.top_scopes())
        var_count = sum(1 for _ in hierarchy.all_vars())
        result["num_top_scopes"] = scope_count
        result["num_variables"] = var_count

        return result

    async def waveform_close(self, session_id: str) -> Dict[str, Any]:
        """
        Close a waveform session and release resources.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary with success status
        """
        success = self.session_manager.close_session(session_id)

        if not success:
            raise SessionError(
                f"Session not found: {session_id}",
                code=ErrorCode.SESSION_NOT_FOUND,
                context={"session_id": session_id},
            )

        return {
            "success": True,
            "session_id": session_id,
            "message": "Session closed successfully",
        }

    async def waveform_list_sessions(self) -> Dict[str, Any]:
        """
        List all active sessions.

        Returns:
            Dictionary with list of session IDs and count
        """
        sessions = self.session_manager.list_sessions()
        return {
            "sessions": sessions,
            "count": len(sessions),
            "max_sessions": self.session_manager.max_sessions,
        }
