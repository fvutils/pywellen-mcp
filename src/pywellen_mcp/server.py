"""MCP server implementation for PyWellen."""

import asyncio
import sys
from typing import Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .session import SessionManager
from .tools_waveform import WaveformTools
from .tools_hierarchy import HierarchyTools
from .tools_signal import SignalTools
from .tools_debug import (
    debug_find_transition,
    debug_trace_causality,
    debug_event_timeline,
    search_by_activity,
    signal_compare,
)
from .tools_format import format_value, format_as_signed
from .tools_llm import (
    query_natural_language,
    signal_summarize,
    recommend_related_signals,
    docs_get_started,
    docs_tool_guide,
)
from .tools_export import (
    export_to_csv,
    export_hierarchy_tree,
    load_signal_list,
    save_signal_list,
    export_signal_data,
)
from .tools_integration import (
    integration_launch_viewer,
    integration_watch_file,
    integration_generate_gtkwave_save,
)
from .errors import WellenMCPError


class PyWellenMCPServer:
    """MCP server for Wellen waveform library."""

    def __init__(self, max_sessions: int = 10, signal_cache_size: int = 100):
        self.app = Server("pywellen-mcp")
        self.session_manager = SessionManager(max_sessions=max_sessions)
        self.waveform_tools = WaveformTools(self.session_manager)
        self.hierarchy_tools = HierarchyTools(self.session_manager)
        self.signal_tools = SignalTools(self.session_manager, cache_size=signal_cache_size)

        # Register handlers
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register MCP protocol handlers."""

        @self.app.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="waveform_open",
                    description=(
                        "Load a waveform file (VCD/FST/GHW) and create a session. "
                        "Returns session_id for subsequent operations. "
                        "Supports multi-threaded parsing for better performance."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Path to waveform file (VCD/FST/GHW format)",
                            },
                            "multi_threaded": {
                                "type": "boolean",
                                "description": "Enable parallel parsing (default: true)",
                                "default": True,
                            },
                            "remove_empty_scopes": {
                                "type": "boolean",
                                "description": "Remove scopes with empty names (default: false)",
                                "default": False,
                            },
                        },
                        "required": ["path"],
                    },
                ),
                Tool(
                    name="waveform_info",
                    description=(
                        "Get metadata about a loaded waveform including format, "
                        "timescale, date, version, and signal counts."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session identifier from waveform_open",
                            },
                        },
                        "required": ["session_id"],
                    },
                ),
                Tool(
                    name="waveform_close",
                    description=(
                        "Close a waveform session and release resources. "
                        "Sessions also auto-expire after 1 hour of inactivity."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session identifier to close",
                            },
                        },
                        "required": ["session_id"],
                    },
                ),
                Tool(
                    name="waveform_list_sessions",
                    description="List all active waveform sessions with their IDs.",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
                Tool(
                    name="hierarchy_list_top_scopes",
                    description=(
                        "List all top-level scopes in the waveform hierarchy. "
                        "Shows scope names, types, and child counts."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session identifier",
                            },
                        },
                        "required": ["session_id"],
                    },
                ),
                Tool(
                    name="hierarchy_get_scope",
                    description=(
                        "Get detailed information about a specific scope including "
                        "its variables and child scopes."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session identifier",
                            },
                            "scope_path": {
                                "type": "string",
                                "description": "Dot-separated scope path (e.g., 'top.cpu.alu')",
                            },
                            "include_variables": {
                                "type": "boolean",
                                "description": "Include variables in scope (default: true)",
                                "default": True,
                            },
                            "include_child_scopes": {
                                "type": "boolean",
                                "description": "Include child scopes (default: true)",
                                "default": True,
                            },
                        },
                        "required": ["session_id", "scope_path"],
                    },
                ),
                Tool(
                    name="hierarchy_list_variables",
                    description=(
                        "List variables with filtering by type, direction, bitwidth, etc. "
                        "Supports pagination for large result sets."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session identifier",
                            },
                            "scope_path": {
                                "type": "string",
                                "description": "Limit to specific scope (null = all variables)",
                            },
                            "var_types": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by types (e.g., ['Wire', 'Reg'])",
                            },
                            "direction": {
                                "type": "string",
                                "description": "Filter by direction (Input/Output/InOut)",
                            },
                            "min_bitwidth": {
                                "type": "integer",
                                "description": "Minimum bitwidth (inclusive)",
                            },
                            "max_bitwidth": {
                                "type": "integer",
                                "description": "Maximum bitwidth (inclusive)",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results (default: 100)",
                                "default": 100,
                            },
                            "offset": {
                                "type": "integer",
                                "description": "Skip first N results (default: 0)",
                                "default": 0,
                            },
                        },
                        "required": ["session_id"],
                    },
                ),
                Tool(
                    name="hierarchy_search",
                    description=(
                        "Search hierarchy by name pattern using regex or substring matching. "
                        "Can search scopes, variables, or both."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session identifier",
                            },
                            "pattern": {
                                "type": "string",
                                "description": "Search pattern (regex or substring)",
                            },
                            "search_in": {
                                "type": "string",
                                "enum": ["scopes", "variables", "both"],
                                "description": "What to search (default: both)",
                                "default": "both",
                            },
                            "case_sensitive": {
                                "type": "boolean",
                                "description": "Case-sensitive matching (default: false)",
                                "default": False,
                            },
                            "regex": {
                                "type": "boolean",
                                "description": "Use regex pattern (default: false)",
                                "default": False,
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Max results per category (default: 100)",
                                "default": 100,
                            },
                        },
                        "required": ["session_id", "pattern"],
                    },
                ),
                Tool(
                    name="signal_get_value",
                    description=(
                        "Query signal value(s) at specific time(s). "
                        "Supports multiple time queries and various output formats."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session identifier",
                            },
                            "variable_path": {
                                "type": "string",
                                "description": "Full hierarchical path to variable",
                            },
                            "times": {
                                "oneOf": [
                                    {"type": "integer"},
                                    {"type": "array", "items": {"type": "integer"}},
                                ],
                                "description": "Single time or list of times to query",
                            },
                            "format": {
                                "type": "string",
                                "enum": ["auto", "int", "hex", "bin", "string"],
                                "description": "Output format (default: auto)",
                                "default": "auto",
                            },
                        },
                        "required": ["session_id", "variable_path", "times"],
                    },
                ),
                Tool(
                    name="signal_get_changes",
                    description=(
                        "Get all value changes for a signal with optional time range filtering. "
                        "Returns (time, value) pairs for each transition."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session identifier",
                            },
                            "variable_path": {
                                "type": "string",
                                "description": "Full hierarchical path to variable",
                            },
                            "start_time": {
                                "type": "integer",
                                "description": "Optional start time (inclusive)",
                            },
                            "end_time": {
                                "type": "integer",
                                "description": "Optional end time (inclusive)",
                            },
                            "max_changes": {
                                "type": "integer",
                                "description": "Optional limit on number of changes",
                            },
                            "format": {
                                "type": "string",
                                "enum": ["auto", "int", "hex", "bin", "string"],
                                "description": "Output format (default: auto)",
                                "default": "auto",
                            },
                        },
                        "required": ["session_id", "variable_path"],
                    },
                ),
                Tool(
                    name="time_get_range",
                    description=(
                        "Get simulation time range including min time, max time, "
                        "and number of time points."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session identifier",
                            },
                        },
                        "required": ["session_id"],
                    },
                ),
                Tool(
                    name="time_convert",
                    description=(
                        "Convert between time indices and actual simulation times. "
                        "Useful for efficient time table navigation."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session identifier",
                            },
                            "indices": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "Time indices to convert to times",
                            },
                            "times": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "Times to find nearest indices for",
                            },
                        },
                        "required": ["session_id"],
                    },
                ),
                Tool(
                    name="signal_get_statistics",
                    description=(
                        "Compute statistics on signal behavior including toggle count, "
                        "unique values, and numeric min/max."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session identifier",
                            },
                            "variable_path": {
                                "type": "string",
                                "description": "Full hierarchical path to variable",
                            },
                            "start_time": {
                                "type": "integer",
                                "description": "Optional start time filter",
                            },
                            "end_time": {
                                "type": "integer",
                                "description": "Optional end time filter",
                            },
                        },
                        "required": ["session_id", "variable_path"],
                    },
                ),
                Tool(
                    name="debug_find_transition",
                    description=(
                        "Find signal transitions matching specific conditions. "
                        "Essential for debugging - find rising/falling edges, value changes, "
                        "or when signals cross thresholds."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session identifier",
                            },
                            "variable_path": {
                                "type": "string",
                                "description": "Full hierarchical path to variable",
                            },
                            "condition": {
                                "type": "string",
                                "enum": ["equals", "not_equals", "greater", "less", "rises", "falls"],
                                "description": "Transition condition to match",
                            },
                            "value": {
                                "type": "string",
                                "description": "Target value (not used for rises/falls)",
                            },
                            "start_time": {
                                "type": "integer",
                                "description": "Optional start of search window",
                            },
                            "end_time": {
                                "type": "integer",
                                "description": "Optional end of search window",
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum transitions to return (default: 100)",
                                "default": 100,
                            },
                        },
                        "required": ["session_id", "variable_path", "condition"],
                    },
                ),
                Tool(
                    name="debug_trace_causality",
                    description=(
                        "Trace potential causes of a signal change. "
                        "Find signals that changed shortly before target transition, "
                        "helping identify root causes in debugging."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session identifier",
                            },
                            "target_path": {
                                "type": "string",
                                "description": "Signal that changed",
                            },
                            "target_time": {
                                "type": "integer",
                                "description": "Time of the target transition",
                            },
                            "search_window": {
                                "type": "integer",
                                "description": "Time before target to search (default: 1000)",
                                "default": 1000,
                            },
                            "related_signals": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional list of signals to examine (null = same scope)",
                            },
                        },
                        "required": ["session_id", "target_path", "target_time"],
                    },
                ),
                Tool(
                    name="debug_event_timeline",
                    description=(
                        "Build chronological timeline of events across multiple signals. "
                        "Unified view of when signals change for understanding sequences."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session identifier",
                            },
                            "signal_paths": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of signals to include in timeline",
                            },
                            "start_time": {
                                "type": "integer",
                                "description": "Timeline start time",
                            },
                            "end_time": {
                                "type": "integer",
                                "description": "Timeline end time",
                            },
                            "max_events": {
                                "type": "integer",
                                "description": "Maximum events to return (default: 1000)",
                                "default": 1000,
                            },
                        },
                        "required": ["session_id", "signal_paths", "start_time", "end_time"],
                    },
                ),
                Tool(
                    name="search_by_activity",
                    description=(
                        "Find signals by toggle activity/change frequency. "
                        "Useful for finding clock signals, static signals, or active state machines."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session identifier",
                            },
                            "scope_path": {
                                "type": "string",
                                "description": "Limit search to specific scope (null = all signals)",
                            },
                            "min_toggles": {
                                "type": "integer",
                                "description": "Minimum number of transitions",
                            },
                            "max_toggles": {
                                "type": "integer",
                                "description": "Maximum number of transitions",
                            },
                            "start_time": {
                                "type": "integer",
                                "description": "Start of analysis window",
                            },
                            "end_time": {
                                "type": "integer",
                                "description": "End of analysis window",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results (default: 100)",
                                "default": 100,
                            },
                        },
                        "required": ["session_id"],
                    },
                ),
                Tool(
                    name="signal_compare",
                    description=(
                        "Compare two signals and find differences. "
                        "Useful for comparing expected vs actual, checking redundancy, "
                        "or finding divergence points."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session identifier",
                            },
                            "signal_path1": {
                                "type": "string",
                                "description": "First signal path",
                            },
                            "signal_path2": {
                                "type": "string",
                                "description": "Second signal path",
                            },
                            "start_time": {
                                "type": "integer",
                                "description": "Start of comparison window",
                            },
                            "end_time": {
                                "type": "integer",
                                "description": "End of comparison window",
                            },
                        },
                        "required": ["session_id", "signal_path1", "signal_path2"],
                    },
                ),
                Tool(
                    name="format_value",
                    description=(
                        "Convert signal value between different representations "
                        "(binary, hex, decimal, octal). Supports auto-detection and bitwidth padding."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "value": {
                                "type": "string",
                                "description": "Input value to convert",
                            },
                            "from_format": {
                                "type": "string",
                                "enum": ["auto", "binary", "hex", "decimal", "octal"],
                                "description": "Input format (default: auto)",
                                "default": "auto",
                            },
                            "to_format": {
                                "type": "string",
                                "enum": ["binary", "hex", "decimal", "octal"],
                                "description": "Output format (default: hex)",
                                "default": "hex",
                            },
                            "bitwidth": {
                                "type": "integer",
                                "description": "Optional bit width for padding",
                            },
                        },
                        "required": ["value"],
                    },
                ),
                Tool(
                    name="format_as_signed",
                    description=(
                        "Interpret bit vector as signed integer using two's complement. "
                        "Useful for displaying signed register values and arithmetic operations."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "value": {
                                "type": "string",
                                "description": "Input value (unsigned interpretation)",
                            },
                            "bitwidth": {
                                "type": "integer",
                                "description": "Number of bits in the value",
                            },
                            "input_format": {
                                "type": "string",
                                "enum": ["auto", "binary", "hex", "decimal"],
                                "description": "Format of input value (default: auto)",
                                "default": "auto",
                            },
                        },
                        "required": ["value", "bitwidth"],
                    },
                ),
                Tool(
                    name="query_natural_language",
                    description=(
                        "Interpret natural language queries and suggest appropriate tool calls. "
                        "Helps map user intent to specific MCP tools and parameters. "
                        "Use this when user queries are ambiguous or exploratory."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Active session identifier",
                            },
                            "query": {
                                "type": "string",
                                "description": "Natural language query (e.g., 'show me all clock signals')",
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of suggestions (default: 10)",
                                "default": 10,
                            },
                        },
                        "required": ["session_id", "query"],
                    },
                ),
                Tool(
                    name="signal_summarize",
                    description=(
                        "Generate concise summary of signal behavior for LLM context efficiency. "
                        "Provides statistics, patterns, and recommendations instead of raw data. "
                        "Use this instead of signal_list_changes for high-level understanding."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Active session identifier",
                            },
                            "variable_path": {
                                "type": "string",
                                "description": "Signal path (e.g., 'top.cpu.state')",
                            },
                            "max_changes": {
                                "type": "integer",
                                "description": "Maximum representative changes to include (default: 20)",
                                "default": 20,
                            },
                            "include_stats": {
                                "type": "boolean",
                                "description": "Include statistical analysis (default: true)",
                                "default": True,
                            },
                        },
                        "required": ["session_id", "variable_path"],
                    },
                ),
                Tool(
                    name="recommend_related_signals",
                    description=(
                        "Recommend signals related to a given signal for deeper analysis. "
                        "Uses heuristics based on naming, scope, and common patterns. "
                        "Helps discover relevant signals without exploring entire hierarchy."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Active session identifier",
                            },
                            "variable_path": {
                                "type": "string",
                                "description": "Reference signal path",
                            },
                            "max_recommendations": {
                                "type": "integer",
                                "description": "Maximum number of recommendations (default: 10)",
                                "default": 10,
                            },
                        },
                        "required": ["session_id", "variable_path"],
                    },
                ),
                Tool(
                    name="docs_get_started",
                    description=(
                        "Get quick-start guide for using PyWellen MCP server. "
                        "Provides overview, workflows, tool categories, and tips. "
                        "Use this to understand available capabilities and common patterns."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
                Tool(
                    name="docs_tool_guide",
                    description=(
                        "Get detailed usage guide for a specific tool. "
                        "Includes parameters, examples, related tools, and common errors. "
                        "Use this for in-depth documentation of a particular tool."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tool_name": {
                                "type": "string",
                                "description": "Name of tool to get documentation for",
                            },
                        },
                        "required": ["tool_name"],
                    },
                ),
                Tool(
                    name="export_to_csv",
                    description=(
                        "Export signal data to CSV format for analysis in spreadsheets or data tools. "
                        "Creates CSV with time column and signal value columns."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Active session identifier",
                            },
                            "signal_paths": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of signal paths to export",
                            },
                            "output_path": {
                                "type": "string",
                                "description": "Path to output CSV file",
                            },
                            "start_time": {
                                "type": "integer",
                                "description": "Optional start time for export range",
                            },
                            "end_time": {
                                "type": "integer",
                                "description": "Optional end time for export range",
                            },
                            "include_header": {
                                "type": "boolean",
                                "description": "Include column headers (default: true)",
                                "default": True,
                            },
                            "time_format": {
                                "type": "string",
                                "enum": ["absolute", "relative"],
                                "description": "Time format - absolute or relative (default: absolute)",
                                "default": "absolute",
                            },
                        },
                        "required": ["session_id", "signal_paths", "output_path"],
                    },
                ),
                Tool(
                    name="export_hierarchy_tree",
                    description=(
                        "Export design hierarchy as structured tree (JSON/YAML/text). "
                        "Useful for visualization and external processing."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Active session identifier",
                            },
                            "output_path": {
                                "type": "string",
                                "description": "Path to output file",
                            },
                            "format": {
                                "type": "string",
                                "enum": ["json", "yaml", "text"],
                                "description": "Output format (default: json)",
                                "default": "json",
                            },
                            "include_variables": {
                                "type": "boolean",
                                "description": "Include variable details (default: true)",
                                "default": True,
                            },
                            "include_metadata": {
                                "type": "boolean",
                                "description": "Include scope metadata (default: true)",
                                "default": True,
                            },
                            "max_depth": {
                                "type": "integer",
                                "description": "Maximum tree depth (null = unlimited)",
                            },
                        },
                        "required": ["session_id", "output_path"],
                    },
                ),
                Tool(
                    name="load_signal_list",
                    description=(
                        "Load signal list from configuration file (JSON/YAML). "
                        "Supports signal groups, filters, and metadata for workflows."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Active session identifier",
                            },
                            "config_path": {
                                "type": "string",
                                "description": "Path to configuration file (.json or .yaml)",
                            },
                        },
                        "required": ["session_id", "config_path"],
                    },
                ),
                Tool(
                    name="save_signal_list",
                    description=(
                        "Save signal list to configuration file for reuse. "
                        "Creates reusable config with signals, groups, filters, and metadata."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Active session identifier",
                            },
                            "output_path": {
                                "type": "string",
                                "description": "Path to output configuration file",
                            },
                            "signal_paths": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of signal paths to save",
                            },
                            "groups": {
                                "type": "object",
                                "description": "Optional signal groups dictionary",
                            },
                            "filters": {
                                "type": "object",
                                "description": "Optional filter configuration",
                            },
                            "metadata": {
                                "type": "object",
                                "description": "Optional metadata dictionary",
                            },
                            "format": {
                                "type": "string",
                                "enum": ["json", "yaml"],
                                "description": "Output format (default: json)",
                                "default": "json",
                            },
                        },
                        "required": ["session_id", "output_path", "signal_paths"],
                    },
                ),
                Tool(
                    name="export_signal_data",
                    description=(
                        "Export single signal data to JSON or CSV. "
                        "Exports all changes with timestamps and values."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Active session identifier",
                            },
                            "signal_path": {
                                "type": "string",
                                "description": "Signal path to export",
                            },
                            "output_path": {
                                "type": "string",
                                "description": "Path to output file",
                            },
                            "format": {
                                "type": "string",
                                "enum": ["json", "csv"],
                                "description": "Output format (default: json)",
                                "default": "json",
                            },
                            "start_time": {
                                "type": "integer",
                                "description": "Optional start time for export range",
                            },
                            "end_time": {
                                "type": "integer",
                                "description": "Optional end time for export range",
                            },
                        },
                        "required": ["session_id", "signal_path", "output_path"],
                    },
                ),
                Tool(
                    name="integration_launch_viewer",
                    description=(
                        "Launch external waveform viewer (GTKWave, Verdi, Simvision, etc). "
                        "Can load waveform file with optional save/config file."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "viewer": {
                                "type": "string",
                                "enum": ["gtkwave", "simvision", "verdi", "dve", "wave", "custom"],
                                "description": "Viewer name or 'custom' for custom command",
                            },
                            "file_path": {
                                "type": "string",
                                "description": "Path to waveform file",
                            },
                            "save_file": {
                                "type": "string",
                                "description": "Optional save/configuration file for viewer",
                            },
                            "additional_args": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Additional command line arguments",
                            },
                            "wait": {
                                "type": "boolean",
                                "description": "Wait for viewer to exit (default: false)",
                                "default": False,
                            },
                        },
                        "required": ["viewer", "file_path"],
                    },
                ),
                Tool(
                    name="integration_watch_file",
                    description=(
                        "Monitor waveform file for changes. "
                        "Useful for live simulation monitoring and auto-reload workflows."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to waveform file to monitor",
                            },
                            "interval": {
                                "type": "integer",
                                "description": "Check interval in seconds (default: 5)",
                                "default": 5,
                            },
                            "max_checks": {
                                "type": "integer",
                                "description": "Maximum checks before returning (default: 60)",
                                "default": 60,
                            },
                        },
                        "required": ["file_path"],
                    },
                ),
                Tool(
                    name="integration_generate_gtkwave_save",
                    description=(
                        "Generate GTKWave save file (.gtkw) for signal viewing. "
                        "Pre-loads specified signals for quick waveform inspection."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Active session identifier",
                            },
                            "output_path": {
                                "type": "string",
                                "description": "Path to output .gtkw file",
                            },
                            "signal_paths": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of signals to include",
                            },
                            "time_range": {
                                "type": "object",
                                "properties": {
                                    "start": {"type": "integer"},
                                    "end": {"type": "integer"},
                                },
                                "description": "Optional time range dict",
                            },
                            "group_signals": {
                                "type": "boolean",
                                "description": "Group signals by hierarchy (default: true)",
                                "default": True,
                            },
                        },
                        "required": ["session_id", "output_path", "signal_paths"],
                    },
                ),
            ]

        @self.app.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            """Handle tool calls."""
            try:
                # Route to appropriate tool handler
                if name == "waveform_open":
                    result = await self.waveform_tools.waveform_open(**arguments)
                elif name == "waveform_info":
                    result = await self.waveform_tools.waveform_info(**arguments)
                elif name == "waveform_close":
                    result = await self.waveform_tools.waveform_close(**arguments)
                elif name == "waveform_list_sessions":
                    result = await self.waveform_tools.waveform_list_sessions()
                elif name == "hierarchy_list_top_scopes":
                    result = await self.hierarchy_tools.hierarchy_list_top_scopes(**arguments)
                elif name == "hierarchy_get_scope":
                    result = await self.hierarchy_tools.hierarchy_get_scope(**arguments)
                elif name == "hierarchy_list_variables":
                    result = await self.hierarchy_tools.hierarchy_list_variables(**arguments)
                elif name == "hierarchy_search":
                    result = await self.hierarchy_tools.hierarchy_search(**arguments)
                elif name == "signal_get_value":
                    result = await self.signal_tools.signal_get_value(**arguments)
                elif name == "signal_get_changes":
                    result = await self.signal_tools.signal_get_changes(**arguments)
                elif name == "time_get_range":
                    result = await self.signal_tools.time_get_range(**arguments)
                elif name == "time_convert":
                    result = await self.signal_tools.time_convert(**arguments)
                elif name == "signal_get_statistics":
                    result = await self.signal_tools.signal_get_statistics(**arguments)
                elif name == "debug_find_transition":
                    result = await debug_find_transition(self.session_manager, **arguments)
                elif name == "debug_trace_causality":
                    result = await debug_trace_causality(self.session_manager, **arguments)
                elif name == "debug_event_timeline":
                    result = await debug_event_timeline(self.session_manager, **arguments)
                elif name == "search_by_activity":
                    result = await search_by_activity(self.session_manager, **arguments)
                elif name == "signal_compare":
                    result = await signal_compare(self.session_manager, **arguments)
                elif name == "format_value":
                    result = await format_value(**arguments)
                elif name == "format_as_signed":
                    result = await format_as_signed(**arguments)
                elif name == "query_natural_language":
                    result = await query_natural_language(self.session_manager, **arguments)
                elif name == "signal_summarize":
                    result = await signal_summarize(self.session_manager, **arguments)
                elif name == "recommend_related_signals":
                    result = await recommend_related_signals(self.session_manager, **arguments)
                elif name == "docs_get_started":
                    result = await docs_get_started()
                elif name == "docs_tool_guide":
                    result = await docs_tool_guide(**arguments)
                elif name == "export_to_csv":
                    result = await export_to_csv(self.session_manager, **arguments)
                elif name == "export_hierarchy_tree":
                    result = await export_hierarchy_tree(self.session_manager, **arguments)
                elif name == "load_signal_list":
                    result = await load_signal_list(self.session_manager, **arguments)
                elif name == "save_signal_list":
                    result = await save_signal_list(self.session_manager, **arguments)
                elif name == "export_signal_data":
                    result = await export_signal_data(self.session_manager, **arguments)
                elif name == "integration_launch_viewer":
                    result = await integration_launch_viewer(**arguments)
                elif name == "integration_watch_file":
                    result = await integration_watch_file(**arguments)
                elif name == "integration_generate_gtkwave_save":
                    result = await integration_generate_gtkwave_save(self.session_manager, **arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")

                # Format result as JSON
                import json

                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            except WellenMCPError as e:
                # Structured error response
                import json

                error_response = e.to_dict()
                return [TextContent(type="text", text=json.dumps(error_response, indent=2))]

            except Exception as e:
                # Unexpected error
                import json

                error_response = {
                    "error": "INTERNAL_ERROR",
                    "message": str(e),
                    "type": type(e).__name__,
                }
                return [TextContent(type="text", text=json.dumps(error_response, indent=2))]

    async def run(self) -> None:
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.app.run(read_stream, write_stream, self.app.create_initialization_options())


def main() -> None:
    """Main entry point for the server."""
    server = PyWellenMCPServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
