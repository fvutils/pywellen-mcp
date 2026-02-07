"""Unit tests for export tools."""

import pytest
import os
import json
import csv
import tempfile
from unittest.mock import Mock, patch, MagicMock
from src.pywellen_mcp.tools_export import (
    export_to_csv,
    export_hierarchy_tree,
    load_signal_list,
    save_signal_list,
    export_signal_data,
)
from src.pywellen_mcp.session import SessionManager
from src.pywellen_mcp.errors import FileError, QueryError


@pytest.fixture
def mock_session_manager():
    """Create a mock session manager."""
    manager = Mock(spec=SessionManager)
    session = Mock()
    session.waveform = Mock()
    session.hierarchy = Mock()
    session.time_table = Mock()
    session.time_table.start_time = Mock(return_value=0)
    session.time_table.end_time = Mock(return_value=1000)
    manager.get_session = Mock(return_value=session)
    return manager, session


class TestExportToCSV:
    """Tests for export_to_csv tool."""
    
    @pytest.mark.asyncio
    async def test_export_basic(self, mock_session_manager, tmp_path):
        """Test basic CSV export."""
        manager, session = mock_session_manager
        
        # Setup mock variables and signal values
        var1 = Mock()
        var2 = Mock()
        session.hierarchy.get_var_by_name = Mock(side_effect=[var1, var2, var1, var2])
        
        # Mock signal changes - use return_value with iterator
        change1_0 = Mock(time=0, value="0")
        change1_10 = Mock(time=10, value="1")
        change2_5 = Mock(time=5, value="0xff")
        
        def get_values_side_effect(var):
            if var == var1:
                return iter([change1_0, change1_10])
            else:
                return iter([change2_5])
        
        session.waveform.get_signal_values = Mock(side_effect=get_values_side_effect)
        
        output_file = tmp_path / "test.csv"
        
        result = await export_to_csv(
            session_manager=manager,
            session_id="test",
            signal_paths=["sig1", "sig2"],
            output_path=str(output_file)
        )
        
        assert result["output_file"] == str(output_file)
        assert result["signals_exported"] == 2
        assert result["rows_written"] > 0
        assert os.path.exists(output_file)
        
        # Verify CSV contents
        with open(output_file, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader)
            assert "Time" in headers[0]
            assert "sig1" in headers
            assert "sig2" in headers
    
    @pytest.mark.asyncio
    async def test_export_with_time_range(self, mock_session_manager, tmp_path):
        """Test CSV export with time filtering."""
        manager, session = mock_session_manager
        
        var1 = Mock()
        session.hierarchy.get_var_by_name = Mock(return_value=var1)
        
        change1 = Mock(time=5, value="0")
        change2 = Mock(time=15, value="1")
        change3 = Mock(time=25, value="0")
        
        session.waveform.get_signal_values = Mock(return_value=[change1, change2, change3])
        
        output_file = tmp_path / "test_range.csv"
        
        result = await export_to_csv(
            session_manager=manager,
            session_id="test",
            signal_paths=["sig1"],
            output_path=str(output_file),
            start_time=10,
            end_time=20
        )
        
        assert result["time_range"]["start"] == 15  # Only change2 in range
        assert result["time_range"]["end"] == 15
    
    @pytest.mark.asyncio
    async def test_export_invalid_signal(self, mock_session_manager, tmp_path):
        """Test export with invalid signal."""
        manager, session = mock_session_manager
        session.hierarchy.get_var_by_name = Mock(return_value=None)
        
        output_file = tmp_path / "test.csv"
        
        with pytest.raises(QueryError):
            await export_to_csv(
                session_manager=manager,
                session_id="test",
                signal_paths=["invalid"],
                output_path=str(output_file)
            )
    
    @pytest.mark.asyncio
    async def test_export_invalid_path(self, mock_session_manager):
        """Test export to invalid directory."""
        manager, session = mock_session_manager
        
        with pytest.raises(FileError):
            await export_to_csv(
                session_manager=manager,
                session_id="test",
                signal_paths=["sig1"],
                output_path="/nonexistent/dir/test.csv"
            )


class TestExportHierarchyTree:
    """Tests for export_hierarchy_tree tool."""
    
    @pytest.mark.asyncio
    async def test_export_json(self, mock_session_manager, tmp_path):
        """Test hierarchy export as JSON."""
        manager, session = mock_session_manager
        
        # Setup mock hierarchy
        top_scope = Mock()
        top_scope.name = "top"
        top_scope.scope_type = "Module"
        top_scope.children = Mock(return_value=[])
        top_scope.variables = Mock(return_value=[])
        
        session.hierarchy.top_scopes = Mock(return_value=[top_scope])
        session.waveform.file_name = Mock(return_value="test.vcd")
        
        output_file = tmp_path / "hierarchy.json"
        
        result = await export_hierarchy_tree(
            session_manager=manager,
            session_id="test",
            output_path=str(output_file),
            format="json"
        )
        
        assert result["output_file"] == str(output_file)
        assert result["format"] == "json"
        assert result["total_scopes"] >= 1
        assert os.path.exists(output_file)
        
        # Verify JSON structure
        with open(output_file, 'r') as f:
            data = json.load(f)
            assert "design" in data
            assert "scopes" in data
    
    @pytest.mark.asyncio
    async def test_export_with_variables(self, mock_session_manager, tmp_path):
        """Test hierarchy export including variables."""
        manager, session = mock_session_manager
        
        # Setup mock hierarchy with variables
        var1 = Mock()
        var1.name = "clk"
        var1.var_type = "Wire"
        var1.length = Mock(return_value=1)
        
        top_scope = Mock()
        top_scope.name = "top"
        top_scope.scope_type = "Module"
        top_scope.children = Mock(return_value=[])
        top_scope.variables = Mock(return_value=[var1])
        
        session.hierarchy.top_scopes = Mock(return_value=[top_scope])
        session.waveform.file_name = Mock(return_value="test.vcd")
        
        output_file = tmp_path / "hierarchy_vars.json"
        
        result = await export_hierarchy_tree(
            session_manager=manager,
            session_id="test",
            output_path=str(output_file),
            format="json",
            include_variables=True
        )
        
        assert result["total_variables"] >= 1
        
        with open(output_file, 'r') as f:
            data = json.load(f)
            assert "variables" in data["scopes"][0]
    
    @pytest.mark.asyncio
    async def test_export_text_format(self, mock_session_manager, tmp_path):
        """Test hierarchy export as text tree."""
        manager, session = mock_session_manager
        
        top_scope = Mock()
        top_scope.name = "top"
        top_scope.scope_type = "Module"
        top_scope.children = Mock(return_value=[])
        top_scope.variables = Mock(return_value=[])
        
        session.hierarchy.top_scopes = Mock(return_value=[top_scope])
        session.waveform.file_name = Mock(return_value="test.vcd")
        
        output_file = tmp_path / "hierarchy.txt"
        
        result = await export_hierarchy_tree(
            session_manager=manager,
            session_id="test",
            output_path=str(output_file),
            format="text"
        )
        
        assert result["format"] == "text"
        assert os.path.exists(output_file)
        
        # Verify text format
        with open(output_file, 'r') as f:
            content = f.read()
            assert "Design:" in content
            assert "top" in content


class TestLoadSignalList:
    """Tests for load_signal_list tool."""
    
    @pytest.mark.asyncio
    async def test_load_json_config(self, mock_session_manager, tmp_path):
        """Test loading JSON configuration."""
        manager, session = mock_session_manager
        
        # Create test config file
        config = {
            "signals": ["top.clk", "top.data"],
            "groups": {
                "control": ["top.valid", "top.ready"]
            }
        }
        
        config_file = tmp_path / "config.json"
        with open(config_file, 'w') as f:
            json.dump(config, f)
        
        # Mock hierarchy
        session.hierarchy.get_var_by_name = Mock(return_value=Mock())
        
        result = await load_signal_list(
            session_manager=manager,
            session_id="test",
            config_path=str(config_file)
        )
        
        assert result["config_file"] == str(config_file)
        assert len(result["signals"]) == 2
        assert "control" in result["groups"]
        assert len(result["groups"]["control"]) == 2
    
    @pytest.mark.asyncio
    async def test_load_nonexistent_file(self, mock_session_manager):
        """Test loading non-existent config file."""
        manager, session = mock_session_manager
        
        with pytest.raises(FileError):
            await load_signal_list(
                session_manager=manager,
                session_id="test",
                config_path="/nonexistent/config.json"
            )
    
    @pytest.mark.asyncio
    async def test_load_invalid_json(self, mock_session_manager, tmp_path):
        """Test loading invalid JSON."""
        manager, session = mock_session_manager
        
        config_file = tmp_path / "invalid.json"
        with open(config_file, 'w') as f:
            f.write("{ invalid json }")
        
        with pytest.raises(FileError):
            await load_signal_list(
                session_manager=manager,
                session_id="test",
                config_path=str(config_file)
            )


class TestSaveSignalList:
    """Tests for save_signal_list tool."""
    
    @pytest.mark.asyncio
    async def test_save_json_config(self, mock_session_manager, tmp_path):
        """Test saving JSON configuration."""
        manager, session = mock_session_manager
        session.hierarchy.get_var_by_name = Mock(return_value=Mock())
        
        output_file = tmp_path / "saved_config.json"
        
        result = await save_signal_list(
            session_manager=manager,
            session_id="test",
            output_path=str(output_file),
            signal_paths=["top.clk", "top.data"],
            groups={"control": ["top.valid"]},
            format="json"
        )
        
        assert result["output_file"] == str(output_file)
        assert result["signals_saved"] == 2
        assert result["groups_saved"] == 1
        assert os.path.exists(output_file)
        
        # Verify saved content
        with open(output_file, 'r') as f:
            data = json.load(f)
            assert "signals" in data
            assert "groups" in data
            assert len(data["signals"]) == 2
    
    @pytest.mark.asyncio
    async def test_save_invalid_signal(self, mock_session_manager, tmp_path):
        """Test saving with invalid signal."""
        manager, session = mock_session_manager
        session.hierarchy.get_var_by_name = Mock(return_value=None)
        
        output_file = tmp_path / "config.json"
        
        with pytest.raises(QueryError):
            await save_signal_list(
                session_manager=manager,
                session_id="test",
                output_path=str(output_file),
                signal_paths=["invalid_signal"]
            )


class TestExportSignalData:
    """Tests for export_signal_data tool."""
    
    @pytest.mark.asyncio
    async def test_export_json(self, mock_session_manager, tmp_path):
        """Test exporting signal data as JSON."""
        manager, session = mock_session_manager
        
        var = Mock()
        session.hierarchy.get_var_by_name = Mock(return_value=var)
        
        change1 = Mock(time=0, value="0")
        change2 = Mock(time=10, value="1")
        session.waveform.get_signal_values = Mock(return_value=[change1, change2])
        
        output_file = tmp_path / "signal.json"
        
        result = await export_signal_data(
            session_manager=manager,
            session_id="test",
            signal_path="top.clk",
            output_path=str(output_file),
            format="json"
        )
        
        assert result["signal_path"] == "top.clk"
        assert result["changes_exported"] == 2
        assert os.path.exists(output_file)
        
        with open(output_file, 'r') as f:
            data = json.load(f)
            assert "signal" in data
            assert "changes" in data
            assert len(data["changes"]) == 2
    
    @pytest.mark.asyncio
    async def test_export_csv(self, mock_session_manager, tmp_path):
        """Test exporting signal data as CSV."""
        manager, session = mock_session_manager
        
        var = Mock()
        session.hierarchy.get_var_by_name = Mock(return_value=var)
        
        change1 = Mock(time=0, value="0")
        change2 = Mock(time=10, value="1")
        session.waveform.get_signal_values = Mock(return_value=[change1, change2])
        
        output_file = tmp_path / "signal.csv"
        
        result = await export_signal_data(
            session_manager=manager,
            session_id="test",
            signal_path="top.clk",
            output_path=str(output_file),
            format="csv"
        )
        
        assert result["format"] == "csv"
        assert os.path.exists(output_file)
        
        with open(output_file, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader)
            assert "Time" in headers
            assert "Value" in headers
