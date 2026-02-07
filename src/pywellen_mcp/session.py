"""Session management for waveform files."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional
from pathlib import Path

try:
    from pywellen import Waveform, Hierarchy, TimeTable
except ImportError:
    # For development/testing without pywellen installed
    Waveform = None  # type: ignore
    Hierarchy = None  # type: ignore
    TimeTable = None  # type: ignore


@dataclass
class WaveformSession:
    """Represents an active waveform session."""

    session_id: str
    filepath: Path
    waveform: "Waveform"
    hierarchy: "Hierarchy"
    time_table: "TimeTable"
    created_at: datetime
    last_accessed: datetime
    multi_threaded: bool = True
    remove_scopes_with_empty_name: bool = False
    bookmarks: list = field(default_factory=list)

    @property
    def file_path(self) -> str:
        """Get file path as string for backward compatibility."""
        return str(self.filepath)

    def update_access_time(self) -> None:
        """Update the last accessed timestamp."""
        self.last_accessed = datetime.now()

    def is_expired(self, timeout: timedelta) -> bool:
        """Check if session has expired based on inactivity timeout."""
        return datetime.now() - self.last_accessed > timeout


class SessionManager:
    """Manages waveform sessions with lifecycle and cleanup."""

    def __init__(
        self,
        max_sessions: int = 10,
        session_timeout: timedelta = timedelta(hours=1),
    ):
        self.max_sessions = max_sessions
        self.session_timeout = session_timeout
        self._sessions: Dict[str, WaveformSession] = {}

    def create_session(
        self,
        filepath: str,
        multi_threaded: bool = True,
        remove_scopes_with_empty_name: bool = False,
    ) -> WaveformSession:
        """
        Create a new waveform session.

        Args:
            filepath: Path to waveform file (VCD/FST/GHW)
            multi_threaded: Enable parallel parsing
            remove_scopes_with_empty_name: Remove scopes with empty names

        Returns:
            WaveformSession object

        Raises:
            RuntimeError: If max sessions exceeded or file cannot be loaded
        """
        if Waveform is None:
            raise RuntimeError("pywellen not available")

        # Clean up expired sessions if at capacity
        if len(self._sessions) >= self.max_sessions:
            self._cleanup_expired()

        if len(self._sessions) >= self.max_sessions:
            raise RuntimeError(
                f"Maximum number of sessions ({self.max_sessions}) reached. "
                "Close existing sessions or wait for timeout."
            )

        # Generate unique session ID
        session_id = str(uuid.uuid4())

        # Load waveform
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Waveform file not found: {filepath}")

        try:
            waveform = Waveform(
                path=str(path),
                multi_threaded=multi_threaded,
                remove_scopes_with_empty_name=remove_scopes_with_empty_name,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load waveform: {e}")

        # Create session
        now = datetime.now()
        session = WaveformSession(
            session_id=session_id,
            filepath=path,
            waveform=waveform,
            hierarchy=waveform.hierarchy,
            time_table=waveform.time_table,
            created_at=now,
            last_accessed=now,
            multi_threaded=multi_threaded,
            remove_scopes_with_empty_name=remove_scopes_with_empty_name,
        )

        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[WaveformSession]:
        """
        Get session by ID and update access time.

        Args:
            session_id: Session identifier

        Returns:
            WaveformSession if found, None otherwise
        """
        session = self._sessions.get(session_id)
        if session:
            session.update_access_time()
        return session

    def close_session(self, session_id: str) -> bool:
        """
        Close and remove a session.

        Args:
            session_id: Session identifier

        Returns:
            True if session was closed, False if not found
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def list_sessions(self) -> list[str]:
        """Get list of active session IDs."""
        return list(self._sessions.keys())

    def get_session_count(self) -> int:
        """Get number of active sessions."""
        return len(self._sessions)

    def _cleanup_expired(self) -> int:
        """
        Remove expired sessions based on timeout.

        Returns:
            Number of sessions removed
        """
        expired = [
            sid for sid, session in self._sessions.items() if session.is_expired(self.session_timeout)
        ]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)

    def cleanup_all(self) -> int:
        """
        Close all sessions.

        Returns:
            Number of sessions closed
        """
        count = len(self._sessions)
        self._sessions.clear()
        return count
