"""Error types and handling for PyWellen MCP server."""

from typing import Optional, Any
from enum import Enum


class ErrorCode(str, Enum):
    """Error codes for structured error reporting."""

    # File errors
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_FORMAT_UNSUPPORTED = "FILE_FORMAT_UNSUPPORTED"
    FILE_CORRUPTED = "FILE_CORRUPTED"
    FILE_ACCESS_DENIED = "FILE_ACCESS_DENIED"

    # Session errors
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    SESSION_LIMIT_EXCEEDED = "SESSION_LIMIT_EXCEEDED"

    # Query errors
    SIGNAL_NOT_FOUND = "SIGNAL_NOT_FOUND"
    SCOPE_NOT_FOUND = "SCOPE_NOT_FOUND"
    INVALID_TIME_RANGE = "INVALID_TIME_RANGE"
    INVALID_PATH = "INVALID_PATH"

    # Resource errors
    MEMORY_LIMIT_EXCEEDED = "MEMORY_LIMIT_EXCEEDED"
    TIMEOUT_EXCEEDED = "TIMEOUT_EXCEEDED"

    # General errors
    INVALID_PARAMETER = "INVALID_PARAMETER"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class WellenMCPError(Exception):
    """Base exception for PyWellen MCP server."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        context: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.context = context or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for JSON serialization."""
        return {
            "error": self.code.value,
            "message": self.message,
            "context": self.context,
        }


class FileError(WellenMCPError):
    """File-related errors."""

    pass


class SessionError(WellenMCPError):
    """Session-related errors."""

    pass


class QueryError(WellenMCPError):
    """Query-related errors."""

    pass


class ResourceError(WellenMCPError):
    """Resource-related errors."""

    pass
