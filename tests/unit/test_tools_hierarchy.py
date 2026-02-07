"""Unit tests for hierarchy navigation tools."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from pywellen_mcp.session import SessionManager
from pywellen_mcp.tools_hierarchy import HierarchyTools
from pywellen_mcp.errors import SessionError, QueryError, ErrorCode


class MockVar:
    """Mock variable object."""

    def __init__(self, name, full_name, var_type="Wire", bitwidth=1, direction="Unknown"):
        self._name = name
        self._full_name = full_name
        self._var_type = var_type
        self._bitwidth = bitwidth
        self._direction = direction

    def name(self, hierarchy):
        return self._name

    def full_name(self, hierarchy):
        return self._full_name

    def var_type(self):
        return self._var_type

    def bitwidth(self):
        return self._bitwidth

    def direction(self):
        return self._direction

    def is_real(self):
        return self._var_type == "Real"

    def is_string(self):
        return self._var_type == "String"

    def is_1bit(self):
        return self._bitwidth == 1

    def enum_type(self, hierarchy):
        return None

    def vhdl_type_name(self, hierarchy):
        return None


class MockScope:
    """Mock scope object."""

    def __init__(self, name, full_name, scope_type="module", vars_list=None, scopes_list=None):
        self._name = name
        self._full_name = full_name
        self._scope_type = scope_type
        self._vars = vars_list or []
        self._scopes = scopes_list or []

    def name(self, hierarchy):
        return self._name

    def full_name(self, hierarchy):
        return self._full_name

    def scope_type(self):
        return self._scope_type

    def vars(self, hierarchy):
        return iter(self._vars)

    def scopes(self, hierarchy):
        return iter(self._scopes)


class MockHierarchy:
    """Mock hierarchy object."""

    def __init__(self, top_scopes_list=None, all_vars_list=None):
        self._top_scopes = top_scopes_list or []
        self._all_vars = all_vars_list or []

    def top_scopes(self):
        return iter(self._top_scopes)

    def all_vars(self):
        return iter(self._all_vars)


class MockWaveform:
    """Mock waveform object."""

    def __init__(self, path: str, multi_threaded: bool = True, remove_scopes_with_empty_name: bool = False, **kwargs):
        # Create a simple hierarchy: top -> cpu -> alu
        alu_vars = [
            MockVar("result", "top.cpu.alu.result", "Wire", 32, "Output"),
            MockVar("a", "top.cpu.alu.a", "Wire", 32, "Input"),
            MockVar("b", "top.cpu.alu.b", "Wire", 32, "Input"),
        ]
        alu_scope = MockScope("alu", "top.cpu.alu", "module", vars_list=alu_vars)

        cpu_vars = [
            MockVar("clk", "top.cpu.clk", "Wire", 1, "Input"),
            MockVar("reset", "top.cpu.reset", "Wire", 1, "Input"),
        ]
        cpu_scope = MockScope("cpu", "top.cpu", "module", vars_list=cpu_vars, scopes_list=[alu_scope])

        top_vars = [
            MockVar("clk", "top.clk", "Wire", 1, "Input"),
        ]
        top_scope = MockScope("top", "top", "module", vars_list=top_vars, scopes_list=[cpu_scope])

        all_vars = [
            MockVar("clk", "top.clk", "Wire", 1, "Input"),
            MockVar("clk", "top.cpu.clk", "Wire", 1, "Input"),
            MockVar("reset", "top.cpu.reset", "Wire", 1, "Input"),
            MockVar("result", "top.cpu.alu.result", "Wire", 32, "Output"),
            MockVar("a", "top.cpu.alu.a", "Wire", 32, "Input"),
            MockVar("b", "top.cpu.alu.b", "Wire", 32, "Input"),
        ]

        self.hierarchy = MockHierarchy(top_scopes_list=[top_scope], all_vars_list=all_vars)
        self.time_table = Mock()


@pytest.fixture
def mock_waveform():
    """Fixture for mock waveform."""
    with patch("pywellen_mcp.session.Waveform", MockWaveform):
        yield MockWaveform


@pytest.fixture
def session_manager():
    """Fixture for SessionManager."""
    return SessionManager(max_sessions=5)


@pytest.fixture
def hierarchy_tools(session_manager):
    """Fixture for HierarchyTools."""
    return HierarchyTools(session_manager)


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary test file."""
    test_file = tmp_path / "test.vcd"
    test_file.write_text("# dummy vcd content")
    return test_file


class TestHierarchyListTopScopes:
    """Test hierarchy_list_top_scopes tool."""

    @pytest.mark.asyncio
    async def test_list_top_scopes_success(self, hierarchy_tools, temp_file, mock_waveform, session_manager):
        """Test listing top scopes."""
        # Create session
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        # List top scopes
        result = await hierarchy_tools.hierarchy_list_top_scopes(session_id)

        assert result["session_id"] == session_id
        assert "top_scopes" in result
        assert result["count"] == 1
        assert len(result["top_scopes"]) == 1

        top_scope = result["top_scopes"][0]
        assert top_scope["name"] == "top"
        assert top_scope["full_name"] == "top"
        assert top_scope["type"] == "module"
        assert top_scope["num_variables"] == 1
        assert top_scope["num_child_scopes"] == 1

    @pytest.mark.asyncio
    async def test_list_top_scopes_session_not_found(self, hierarchy_tools):
        """Test with invalid session."""
        with pytest.raises(SessionError) as exc_info:
            await hierarchy_tools.hierarchy_list_top_scopes("invalid-id")
        assert exc_info.value.code == ErrorCode.SESSION_NOT_FOUND


class TestHierarchyGetScope:
    """Test hierarchy_get_scope tool."""

    @pytest.mark.asyncio
    async def test_get_scope_top_level(self, hierarchy_tools, temp_file, mock_waveform, session_manager):
        """Test getting top-level scope."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        result = await hierarchy_tools.hierarchy_get_scope(session_id, "top")

        assert result["name"] == "top"
        assert result["full_name"] == "top"
        assert result["type"] == "module"
        assert "variables" in result
        assert len(result["variables"]) == 1
        assert "child_scopes" in result
        assert len(result["child_scopes"]) == 1

    @pytest.mark.asyncio
    async def test_get_scope_nested(self, hierarchy_tools, temp_file, mock_waveform, session_manager):
        """Test getting nested scope."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        result = await hierarchy_tools.hierarchy_get_scope(session_id, "top.cpu.alu")

        assert result["name"] == "alu"
        assert result["full_name"] == "top.cpu.alu"
        assert result["type"] == "module"
        assert len(result["variables"]) == 3
        assert len(result["child_scopes"]) == 0

    @pytest.mark.asyncio
    async def test_get_scope_without_children(self, hierarchy_tools, temp_file, mock_waveform, session_manager):
        """Test getting scope without including children."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        result = await hierarchy_tools.hierarchy_get_scope(
            session_id,
            "top",
            include_variables=False,
            include_child_scopes=False,
        )

        assert result["name"] == "top"
        assert "variables" not in result
        assert "child_scopes" not in result

    @pytest.mark.asyncio
    async def test_get_scope_not_found(self, hierarchy_tools, temp_file, mock_waveform, session_manager):
        """Test with non-existent scope."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        with pytest.raises(QueryError) as exc_info:
            await hierarchy_tools.hierarchy_get_scope(session_id, "top.nonexistent")
        assert exc_info.value.code == ErrorCode.SCOPE_NOT_FOUND


class TestHierarchyListVariables:
    """Test hierarchy_list_variables tool."""

    @pytest.mark.asyncio
    async def test_list_all_variables(self, hierarchy_tools, temp_file, mock_waveform, session_manager):
        """Test listing all variables."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        result = await hierarchy_tools.hierarchy_list_variables(session_id)

        assert result["session_id"] == session_id
        assert len(result["variables"]) == 6
        assert result["pagination"]["total_matched"] == 6

    @pytest.mark.asyncio
    async def test_list_variables_in_scope(self, hierarchy_tools, temp_file, mock_waveform, session_manager):
        """Test listing variables in specific scope."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        result = await hierarchy_tools.hierarchy_list_variables(session_id, scope_path="top.cpu.alu")

        assert len(result["variables"]) == 3
        assert all(v["full_name"].startswith("top.cpu.alu.") for v in result["variables"])

    @pytest.mark.asyncio
    async def test_filter_by_bitwidth(self, hierarchy_tools, temp_file, mock_waveform, session_manager):
        """Test filtering by bitwidth."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        result = await hierarchy_tools.hierarchy_list_variables(
            session_id,
            min_bitwidth=32,
        )

        assert len(result["variables"]) == 3
        assert all(v["bitwidth"] == 32 for v in result["variables"])

    @pytest.mark.asyncio
    async def test_filter_by_direction(self, hierarchy_tools, temp_file, mock_waveform, session_manager):
        """Test filtering by direction."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        result = await hierarchy_tools.hierarchy_list_variables(
            session_id,
            direction="Input",
        )

        # Should find: top.clk, top.cpu.clk, top.cpu.reset, top.cpu.alu.a, top.cpu.alu.b
        assert len(result["variables"]) == 5
        assert all(v["direction"] == "Input" for v in result["variables"])

    @pytest.mark.asyncio
    async def test_pagination(self, hierarchy_tools, temp_file, mock_waveform, session_manager):
        """Test pagination."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        # Get first 2
        result1 = await hierarchy_tools.hierarchy_list_variables(session_id, limit=2, offset=0)
        assert len(result1["variables"]) == 2
        assert result1["pagination"]["has_more"] is True

        # Get next 2
        result2 = await hierarchy_tools.hierarchy_list_variables(session_id, limit=2, offset=2)
        assert len(result2["variables"]) == 2

        # Get last 2
        result3 = await hierarchy_tools.hierarchy_list_variables(session_id, limit=2, offset=4)
        assert len(result3["variables"]) == 2
        assert result3["pagination"]["has_more"] is False


class TestHierarchySearch:
    """Test hierarchy_search tool."""

    @pytest.mark.asyncio
    async def test_search_substring(self, hierarchy_tools, temp_file, mock_waveform, session_manager):
        """Test substring search."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        result = await hierarchy_tools.hierarchy_search(session_id, "clk")

        assert "matching_variables" in result
        assert len(result["matching_variables"]) == 2
        assert all("clk" in v["full_name"] for v in result["matching_variables"])

    @pytest.mark.asyncio
    async def test_search_case_sensitive(self, hierarchy_tools, temp_file, mock_waveform, session_manager):
        """Test case-sensitive search."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        # Case insensitive (default)
        result1 = await hierarchy_tools.hierarchy_search(session_id, "CLK")
        assert len(result1["matching_variables"]) == 2

        # Case sensitive
        result2 = await hierarchy_tools.hierarchy_search(session_id, "CLK", case_sensitive=True)
        assert len(result2["matching_variables"]) == 0

    @pytest.mark.asyncio
    async def test_search_regex(self, hierarchy_tools, temp_file, mock_waveform, session_manager):
        """Test regex search."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        result = await hierarchy_tools.hierarchy_search(
            session_id,
            r"top\.cpu\.(clk|reset)",
            regex=True,
        )

        assert len(result["matching_variables"]) == 2
        names = [v["full_name"] for v in result["matching_variables"]]
        assert "top.cpu.clk" in names
        assert "top.cpu.reset" in names

    @pytest.mark.asyncio
    async def test_search_scopes_only(self, hierarchy_tools, temp_file, mock_waveform, session_manager):
        """Test searching only scopes."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        result = await hierarchy_tools.hierarchy_search(session_id, "cpu", search_in="scopes")

        assert "matching_scopes" in result
        assert "matching_variables" not in result
        # Should find both "top.cpu" and "top.cpu.alu" (both contain "cpu")
        assert len(result["matching_scopes"]) == 2
        scope_names = [s["full_name"] for s in result["matching_scopes"]]
        assert "top.cpu" in scope_names

    @pytest.mark.asyncio
    async def test_search_invalid_regex(self, hierarchy_tools, temp_file, mock_waveform, session_manager):
        """Test with invalid regex pattern."""
        session = session_manager.create_session(str(temp_file))
        session_id = session.session_id

        with pytest.raises(QueryError) as exc_info:
            await hierarchy_tools.hierarchy_search(session_id, "[invalid(", regex=True)
        assert exc_info.value.code == ErrorCode.INVALID_PARAMETER
