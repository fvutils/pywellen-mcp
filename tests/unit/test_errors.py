"""Unit tests for error handling."""

import pytest
from pywellen_mcp.errors import (
    ErrorCode,
    WellenMCPError,
    FileError,
    SessionError,
    QueryError,
    ResourceError,
)


class TestErrorCode:
    """Test error code enum."""

    def test_error_codes_exist(self):
        """Test that expected error codes are defined."""
        assert ErrorCode.FILE_NOT_FOUND
        assert ErrorCode.SESSION_NOT_FOUND
        assert ErrorCode.SIGNAL_NOT_FOUND
        assert ErrorCode.INVALID_PARAMETER
        assert ErrorCode.INTERNAL_ERROR


class TestWellenMCPError:
    """Test base error class."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = WellenMCPError("Test error")
        assert str(error) == "Test error"
        assert error.code == ErrorCode.INTERNAL_ERROR
        assert error.context == {}

    def test_error_with_code(self):
        """Test error with specific code."""
        error = WellenMCPError("Test error", code=ErrorCode.FILE_NOT_FOUND)
        assert error.code == ErrorCode.FILE_NOT_FOUND

    def test_error_with_context(self):
        """Test error with context."""
        context = {"path": "/test/file.vcd", "line": 42}
        error = WellenMCPError("Test error", context=context)
        assert error.context == context

    def test_error_to_dict(self):
        """Test error serialization."""
        error = WellenMCPError(
            "Test error",
            code=ErrorCode.FILE_NOT_FOUND,
            context={"path": "/test/file.vcd"},
        )

        result = error.to_dict()
        assert result["error"] == "FILE_NOT_FOUND"
        assert result["message"] == "Test error"
        assert result["context"]["path"] == "/test/file.vcd"


class TestSpecificErrors:
    """Test specific error types."""

    def test_file_error(self):
        """Test FileError."""
        error = FileError("File not found", code=ErrorCode.FILE_NOT_FOUND)
        assert isinstance(error, WellenMCPError)
        assert error.code == ErrorCode.FILE_NOT_FOUND

    def test_session_error(self):
        """Test SessionError."""
        error = SessionError("Session not found", code=ErrorCode.SESSION_NOT_FOUND)
        assert isinstance(error, WellenMCPError)
        assert error.code == ErrorCode.SESSION_NOT_FOUND

    def test_query_error(self):
        """Test QueryError."""
        error = QueryError("Signal not found", code=ErrorCode.SIGNAL_NOT_FOUND)
        assert isinstance(error, WellenMCPError)
        assert error.code == ErrorCode.SIGNAL_NOT_FOUND

    def test_resource_error(self):
        """Test ResourceError."""
        error = ResourceError("Memory exceeded", code=ErrorCode.MEMORY_LIMIT_EXCEEDED)
        assert isinstance(error, WellenMCPError)
        assert error.code == ErrorCode.MEMORY_LIMIT_EXCEEDED
