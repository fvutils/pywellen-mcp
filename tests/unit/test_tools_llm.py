"""Unit tests for LLM optimization tools."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from src.pywellen_mcp.tools_llm import (
    query_natural_language,
    signal_summarize,
    recommend_related_signals,
    docs_get_started,
    docs_tool_guide,
)
from src.pywellen_mcp.session import SessionManager
from src.pywellen_mcp.errors import SessionError


@pytest.fixture
def mock_session():
    """Create a mock waveform session."""
    session = Mock()
    session.waveform = Mock()
    session.hierarchy = Mock()
    return session


@pytest.fixture
def mock_session_manager(mock_session):
    """Create a mock session manager."""
    manager = Mock(spec=SessionManager)
    manager.get_session = Mock(return_value=mock_session)
    return manager


class TestQueryNaturalLanguage:
    """Tests for query_natural_language tool."""
    
    @pytest.mark.asyncio
    async def test_clock_signal_query(self, mock_session_manager):
        """Test query for finding clock signals."""
        result = await query_natural_language(
            session_manager=mock_session_manager,
            session_id="test_session",
            query="show me all clock signals"
        )
        
        assert result["interpreted_intent"] == "Find clock signals"
        assert len(result["suggested_tools"]) > 0
        assert any(t["tool"] == "search_by_activity" for t in result["suggested_tools"])
        assert any(t["tool"] == "hierarchy_search" for t in result["suggested_tools"])
        assert len(result["reasoning"]) > 0
    
    @pytest.mark.asyncio
    async def test_reset_signal_query(self, mock_session_manager):
        """Test query for finding reset signals."""
        result = await query_natural_language(
            session_manager=mock_session_manager,
            session_id="test_session",
            query="find reset signals"
        )
        
        assert result["interpreted_intent"] == "Find reset signals"
        assert any(t["tool"] == "hierarchy_search" for t in result["suggested_tools"])
        suggested = next(t for t in result["suggested_tools"] if t["tool"] == "hierarchy_search")
        assert suggested["parameters"]["pattern"] == r"(reset|rst)"
    
    @pytest.mark.asyncio
    async def test_causality_query(self, mock_session_manager):
        """Test query for causality tracing."""
        result = await query_natural_language(
            session_manager=mock_session_manager,
            session_id="test_session",
            query="what caused the error signal"
        )
        
        assert result["interpreted_intent"] == "Trace causality for signal change"
        assert any(t["tool"] == "debug_trace_causality" for t in result["suggested_tools"])
    
    @pytest.mark.asyncio
    async def test_comparison_query(self, mock_session_manager):
        """Test query for signal comparison."""
        result = await query_natural_language(
            session_manager=mock_session_manager,
            session_id="test_session",
            query="compare expected and actual outputs"
        )
        
        assert result["interpreted_intent"] == "Compare two signals"
        assert any(t["tool"] == "signal_compare" for t in result["suggested_tools"])
    
    @pytest.mark.asyncio
    async def test_edge_detection_query(self, mock_session_manager):
        """Test query for edge detection."""
        result = await query_natural_language(
            session_manager=mock_session_manager,
            session_id="test_session",
            query="find all rising edges"
        )
        
        assert result["interpreted_intent"] == "Find signal transitions/edges"
        suggested = next(t for t in result["suggested_tools"] if t["tool"] == "debug_find_transition")
        assert suggested["parameters"]["condition"] == "rises"
    
    @pytest.mark.asyncio
    async def test_generic_query(self, mock_session_manager):
        """Test generic/unrecognized query."""
        result = await query_natural_language(
            session_manager=mock_session_manager,
            session_id="test_session",
            query="tell me about this waveform"
        )
        
        assert result["interpreted_intent"] == "General waveform exploration"
        assert any(t["tool"] == "waveform_info" for t in result["suggested_tools"])
    
    @pytest.mark.asyncio
    async def test_max_results_limit(self, mock_session_manager):
        """Test max_results parameter limits suggestions."""
        result = await query_natural_language(
            session_manager=mock_session_manager,
            session_id="test_session",
            query="show me all clock signals",
            max_results=2
        )
        
        assert len(result["suggested_tools"]) <= 2
    
    @pytest.mark.asyncio
    async def test_invalid_session(self):
        """Test with invalid session ID."""
        manager = Mock(spec=SessionManager)
        manager.get_session = Mock(side_effect=SessionError("NOT_FOUND", "Session not found"))
        
        with pytest.raises(SessionError):
            await query_natural_language(
                session_manager=manager,
                session_id="invalid",
                query="test"
            )


class TestSignalSummarize:
    """Tests for signal_summarize tool."""
    
    @pytest.mark.asyncio
    async def test_summarize_clock_signal(self, mock_session_manager):
        """Test summarizing a clock signal."""
        # Mock signal_list_changes
        with patch.object(mock_session_manager, 'get_session', return_value=mock_session), \
             patch('src.pywellen_mcp.tools_llm.signal_list_changes', new_callable=AsyncMock) as mock_list:
            
            # Create periodic clock pattern
            mock_list.return_value = {
                "changes": [
                    {"time": 0, "value": "0"},
                    {"time": 10, "value": "1"},
                    {"time": 20, "value": "0"},
                    {"time": 30, "value": "1"},
                    {"time": 40, "value": "0"},
                    {"time": 50, "value": "1"},
                ]
            }
            
            result = await signal_summarize(session_manager=mock_session_manager, 
                session_id="test_session",
                variable_path="top.clk"
            )
        
        assert result["signal_name"] == "top.clk"
        assert result["total_changes"] == 6
        assert "periodic" in result["patterns"]
        assert "statistics" in result
        assert result["statistics"]["toggle_count"] == 5
        assert "likely_clock" in result["patterns"]
        assert len(result["recommendations"]) > 0
    
    @pytest.mark.asyncio
    async def test_summarize_constant_signal(self, mock_session_manager):
        """Test summarizing a constant signal."""
        with patch.object(mock_session_manager, 'get_session', return_value=mock_session), \
             patch('src.pywellen_mcp.tools_llm.signal_list_changes', new_callable=AsyncMock) as mock_list:
            
            mock_list.return_value = {"changes": []}
            
            result = await signal_summarize(session_manager=mock_session_manager, 
                session_id="test_session",
                variable_path="top.const_sig"
            )
        
        assert result["total_changes"] == 0
        assert "constant" in result["patterns"]
        assert "constant value" in result["summary"]
    
    @pytest.mark.asyncio
    async def test_summarize_low_activity(self, mock_session_manager):
        """Test summarizing a low-activity signal."""
        with patch.object(mock_session_manager, 'get_session', return_value=mock_session), \
             patch('src.pywellen_mcp.tools_llm.signal_list_changes', new_callable=AsyncMock) as mock_list:
            
            mock_list.return_value = {
                "changes": [
                    {"time": 0, "value": "0"},
                    {"time": 1000, "value": "1"},
                    {"time": 5000, "value": "0"},
                ]
            }
            
            result = await signal_summarize(session_manager=mock_session_manager, 
                session_id="test_session",
                variable_path="top.enable"
            )
        
        assert result["total_changes"] == 3
        assert "low_activity" in result["patterns"]
        assert result["statistics"]["toggle_count"] == 2
    
    @pytest.mark.asyncio
    async def test_max_changes_truncation(self, mock_session_manager):
        """Test truncation with max_changes."""
        with patch.object(mock_session_manager, 'get_session', return_value=mock_session), \
             patch('src.pywellen_mcp.tools_llm.signal_list_changes', new_callable=AsyncMock) as mock_list:
            
            # Create 100 changes
            changes = [{"time": i * 10, "value": str(i % 2)} for i in range(100)]
            mock_list.return_value = {"changes": changes}
            
            result = await signal_summarize(session_manager=mock_session_manager, 
                session_id="test_session",
                variable_path="top.sig",
                max_changes=10
            )
        
        assert result["total_changes"] == 100
        assert len(result["representative_changes"]) == 10
        assert result["truncated"] is True
    
    @pytest.mark.asyncio
    async def test_no_statistics(self, mock_session_manager):
        """Test with statistics disabled."""
        with patch.object(mock_session_manager, 'get_session', return_value=mock_session), \
             patch('src.pywellen_mcp.tools_llm.signal_list_changes', new_callable=AsyncMock) as mock_list:
            
            mock_list.return_value = {
                "changes": [
                    {"time": 0, "value": "0"},
                    {"time": 10, "value": "1"},
                ]
            }
            
            result = await signal_summarize(session_manager=mock_session_manager, 
                session_id="test_session",
                variable_path="top.sig",
                include_stats=False
            )
        
        assert result["statistics"] == {}


class TestRecommendRelatedSignals:
    """Tests for recommend_related_signals tool."""
    
    @pytest.mark.asyncio
    async def test_recommend_same_scope_signals(self, mock_session_manager):
        """Test recommending signals in same scope."""
        with patch.object(mock_session_manager, 'get_session', return_value=mock_session), \
             patch('src.pywellen_mcp.tools_llm.hierarchy_get_scope', new_callable=AsyncMock) as mock_scope:
            
            mock_scope.return_value = {
                "variables": [
                    {"name": "clk"},
                    {"name": "data"},
                    {"name": "valid"},
                    {"name": "ready"},
                ]
            }
            
            result = await recommend_related_signals(session_manager=mock_session_manager, 
                session_id="test_session",
                variable_path="top.cpu.clk"
            )
        
        assert result["reference_signal"] == "top.cpu.clk"
        assert len(result["recommendations"]) > 0
        assert "same_scope" in result["categories"]
        assert len(result["categories"]["same_scope"]) == 3  # All except clk itself
    
    @pytest.mark.asyncio
    async def test_recommend_complementary_patterns(self, mock_session_manager):
        """Test complementary pattern detection."""
        with patch.object(mock_session_manager, 'get_session', return_value=mock_session), \
             patch('src.pywellen_mcp.tools_llm.hierarchy_get_scope', new_callable=AsyncMock) as mock_scope:
            
            mock_scope.return_value = {"variables": []}
            
            result = await recommend_related_signals(session_manager=mock_session_manager, 
                session_id="test_session",
                variable_path="top.req"
            )
        
        assert "complementary" in result["categories"]
        # Should suggest ack, grant, ready for req signal
        patterns = [r["pattern"] for r in result["categories"]["complementary"]]
        assert any("ack" in p or "grant" in p or "ready" in p for p in patterns)
    
    @pytest.mark.asyncio
    async def test_recommend_control_signals(self, mock_session_manager):
        """Test control signal recommendations."""
        with patch.object(mock_session_manager, 'get_session', return_value=mock_session), \
             patch('src.pywellen_mcp.tools_llm.hierarchy_get_scope', new_callable=AsyncMock) as mock_scope:
            
            mock_scope.return_value = {"variables": []}
            
            result = await recommend_related_signals(session_manager=mock_session_manager, 
                session_id="test_session",
                variable_path="top.data"
            )
        
        assert "control_flow" in result["categories"]
        assert len(result["categories"]["control_flow"]) > 0
    
    @pytest.mark.asyncio
    async def test_max_recommendations_limit(self, mock_session_manager):
        """Test max_recommendations parameter."""
        with patch.object(mock_session_manager, 'get_session', return_value=mock_session), \
             patch('src.pywellen_mcp.tools_llm.hierarchy_get_scope', new_callable=AsyncMock) as mock_scope:
            
            # Create many variables
            mock_scope.return_value = {
                "variables": [{"name": f"sig{i}"} for i in range(50)]
            }
            
            result = await recommend_related_signals(session_manager=mock_session_manager, 
                session_id="test_session",
                variable_path="top.clk",
                max_recommendations=5
            )
        
        assert len(result["recommendations"]) <= 5
    
    @pytest.mark.asyncio
    async def test_single_level_signal(self, mock_session_manager):
        """Test signal without scope path."""
        with patch.object(mock_session_manager, 'get_session', return_value=mock_session):
            result = await recommend_related_signals(session_manager=mock_session_manager, 
                session_id="test_session",
                variable_path="clk"
            )
        
        assert result["reference_signal"] == "clk"
        assert "recommendations" in result


class TestDocsGetStarted:
    """Tests for docs_get_started tool."""
    
    @pytest.mark.asyncio
    async def test_get_started_structure(self):
        """Test get_started returns proper structure."""
        result = await docs_get_started()
        
        assert "overview" in result
        assert "quick_start" in result
        assert "common_workflows" in result
        assert "tool_categories" in result
        assert "tips" in result
    
    @pytest.mark.asyncio
    async def test_get_started_overview(self):
        """Test overview section."""
        result = await docs_get_started()
        
        assert "name" in result["overview"]
        assert "PyWellen" in result["overview"]["name"]
        assert "capabilities" in result["overview"]
        assert len(result["overview"]["capabilities"]) > 0
    
    @pytest.mark.asyncio
    async def test_get_started_workflows(self):
        """Test common workflows."""
        result = await docs_get_started()
        
        assert "debugging" in result["common_workflows"]
        assert "clock_analysis" in result["common_workflows"]
        assert "signal_comparison" in result["common_workflows"]
        assert len(result["common_workflows"]["debugging"]) > 0
    
    @pytest.mark.asyncio
    async def test_get_started_tool_categories(self):
        """Test tool categories."""
        result = await docs_get_started()
        
        assert "session_management" in result["tool_categories"]
        assert "hierarchy_navigation" in result["tool_categories"]
        assert "llm_optimization" in result["tool_categories"]
        assert "waveform_open" in result["tool_categories"]["session_management"]


class TestDocsToolGuide:
    """Tests for docs_tool_guide tool."""
    
    @pytest.mark.asyncio
    async def test_documented_tool(self):
        """Test getting guide for documented tool."""
        result = await docs_tool_guide(tool_name="waveform_open")
        
        assert result["tool_name"] == "waveform_open"
        assert "description" in result
        assert "parameters" in result
        assert "returns" in result
        assert "examples" in result
        assert "related_tools" in result
        assert "common_errors" in result
    
    @pytest.mark.asyncio
    async def test_signal_get_value_guide(self):
        """Test signal_get_value documentation."""
        result = await docs_tool_guide(tool_name="signal_get_value")
        
        assert "session_id" in result["parameters"]
        assert "variable_path" in result["parameters"]
        assert len(result["examples"]) > 0
        assert len(result["related_tools"]) > 0
    
    @pytest.mark.asyncio
    async def test_debug_tool_guide(self):
        """Test debug tool documentation."""
        result = await docs_tool_guide(tool_name="debug_trace_causality")
        
        assert "causality" in result["description"].lower()
        assert "target_path" in result["parameters"]
        assert "target_time" in result["parameters"]
    
    @pytest.mark.asyncio
    async def test_undocumented_tool(self):
        """Test getting guide for undocumented tool."""
        result = await docs_tool_guide(tool_name="unknown_tool")
        
        assert result["tool_name"] == "unknown_tool"
        assert result["status"] == "not_documented"
        assert "suggestion" in result
    
    @pytest.mark.asyncio
    async def test_signal_summarize_guide(self):
        """Test signal_summarize documentation."""
        result = await docs_tool_guide(tool_name="signal_summarize")
        
        assert "LLM" in result["description"]
        assert "max_changes" in result["parameters"]
        assert len(result["examples"]) > 0
