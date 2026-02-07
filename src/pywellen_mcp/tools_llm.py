"""
LLM optimization and educational support tools for PyWellen MCP server.

This module provides tools specifically designed for LLM interaction:
- Natural language query interpretation
- Context-efficient signal summarization
- Signal relationship recommendations
- Educational documentation and guidance
"""

from typing import Any, Dict, List, Optional
from .session import SessionManager
from .errors import SessionError, QueryError


async def query_natural_language(
    session_manager: SessionManager,
    session_id: str,
    query: str,
    max_results: Optional[int] = 10
) -> Dict[str, Any]:
    """
    Interpret natural language queries and suggest appropriate tool calls.
    
    This tool helps LLMs understand user intent and map it to specific MCP tools.
    It analyzes the query and recommends which tools to call with what parameters.
    
    Args:
        session_id: Active waveform session ID
        query: Natural language query (e.g., "show me all clock signals")
        max_results: Maximum number of suggestions to return
        
    Returns:
        Dictionary containing:
        - interpreted_intent: What the user is trying to do
        - suggested_tools: List of tool calls with parameters
        - reasoning: Why these tools were chosen
        - example_usage: How to execute the suggestions
        
    Examples:
        Query: "show me all clock signals"
        -> Suggests: search_by_activity (high toggles) or hierarchy_search (pattern="clk")
        
        Query: "what caused the error signal to go high at time 5000?"
        -> Suggests: debug_trace_causality at target_time=5000
        
        Query: "compare expected and actual outputs"
        -> Suggests: signal_compare with both signal paths
    """
    session = session_manager.get_session(session_id)
    
    # Normalize query
    query_lower = query.lower().strip()
    
    # Pattern matching for common queries
    suggestions = []
    intent = ""
    reasoning = []
    
    # Clock signal detection
    if any(word in query_lower for word in ["clock", "clk", "clocks"]):
        intent = "Find clock signals"
        suggestions.append({
            "tool": "search_by_activity",
            "parameters": {
                "session_id": session_id,
                "min_toggles": 100,
                "limit": max_results
            },
            "priority": "high"
        })
        suggestions.append({
            "tool": "hierarchy_search",
            "parameters": {
                "session_id": session_id,
                "pattern": "clk",
                "search_in": "variables",
                "case_sensitive": False,
                "max_results": max_results
            },
            "priority": "medium"
        })
        reasoning.append("High-activity signals likely to be clocks")
        reasoning.append("Signal names containing 'clk' likely to be clocks")
    
    # Reset signal detection
    elif any(word in query_lower for word in ["reset", "rst"]):
        intent = "Find reset signals"
        suggestions.append({
            "tool": "hierarchy_search",
            "parameters": {
                "session_id": session_id,
                "pattern": r"(reset|rst)",
                "search_in": "variables",
                "case_sensitive": False,
                "use_regex": True,
                "max_results": max_results
            },
            "priority": "high"
        })
        reasoning.append("Search for signals with 'reset' or 'rst' in name")
    
    # Causality tracing
    elif any(phrase in query_lower for phrase in ["what caused", "why did", "cause of", "root cause"]):
        intent = "Trace causality for signal change"
        # Try to extract signal name and time
        suggestions.append({
            "tool": "debug_trace_causality",
            "parameters": {
                "session_id": session_id,
                "target_path": "<extract from query>",
                "target_time": "<extract from query>",
                "search_window": 500
            },
            "priority": "high",
            "note": "Extract target signal path and time from query"
        })
        reasoning.append("Use causality tracing to find related signal changes")
    
    # Signal comparison
    elif any(word in query_lower for word in ["compare", "difference", "differ", "match"]):
        intent = "Compare two signals"
        suggestions.append({
            "tool": "signal_compare",
            "parameters": {
                "session_id": session_id,
                "signal_path1": "<extract from query>",
                "signal_path2": "<extract from query>"
            },
            "priority": "high",
            "note": "Extract both signal paths from query"
        })
        reasoning.append("Compare signals to find differences and match percentage")
    
    # Rising/falling edge detection
    elif any(word in query_lower for word in ["rising edge", "falling edge", "edge", "transition"]):
        intent = "Find signal transitions/edges"
        condition = "rises" if "rising" in query_lower or "rise" in query_lower else "falls"
        suggestions.append({
            "tool": "debug_find_transition",
            "parameters": {
                "session_id": session_id,
                "variable_path": "<extract from query>",
                "condition": condition,
                "max_results": max_results
            },
            "priority": "high",
            "note": "Extract signal path from query"
        })
        reasoning.append(f"Find {condition} transitions in signal")
    
    # Event timeline
    elif any(phrase in query_lower for phrase in ["timeline", "sequence", "order of events", "what happened"]):
        intent = "Build event timeline"
        suggestions.append({
            "tool": "debug_event_timeline",
            "parameters": {
                "session_id": session_id,
                "signal_paths": ["<extract from query>"],
                "max_events": 100
            },
            "priority": "high",
            "note": "Extract signal paths from query"
        })
        reasoning.append("Build chronological timeline of signal changes")
    
    # Signal value queries
    elif any(phrase in query_lower for phrase in ["value of", "what is", "show value", "get value"]):
        intent = "Get signal value"
        suggestions.append({
            "tool": "signal_get_value",
            "parameters": {
                "session_id": session_id,
                "variable_path": "<extract from query>",
                "time": "<extract from query or use 'current'>"
            },
            "priority": "high",
            "note": "Extract signal path and time from query"
        })
        reasoning.append("Retrieve signal value at specific time")
    
    # List signals/variables
    elif any(phrase in query_lower for phrase in ["list", "show all", "find all", "get all"]) and \
         any(word in query_lower for word in ["signal", "variable", "wire", "reg"]):
        intent = "List signals/variables"
        suggestions.append({
            "tool": "hierarchy_list_variables",
            "parameters": {
                "session_id": session_id,
                "limit": max_results
            },
            "priority": "high"
        })
        reasoning.append("List all variables in design")
    
    # Hierarchy exploration
    elif any(word in query_lower for word in ["hierarchy", "structure", "modules", "scopes"]):
        intent = "Explore design hierarchy"
        suggestions.append({
            "tool": "hierarchy_list_top_scopes",
            "parameters": {
                "session_id": session_id
            },
            "priority": "high"
        })
        reasoning.append("List top-level design scopes")
    
    # Default: general exploration
    else:
        intent = "General waveform exploration"
        suggestions.append({
            "tool": "waveform_info",
            "parameters": {
                "session_id": session_id
            },
            "priority": "high"
        })
        suggestions.append({
            "tool": "hierarchy_list_top_scopes",
            "parameters": {
                "session_id": session_id
            },
            "priority": "medium"
        })
        reasoning.append("Start with waveform metadata and top-level structure")
    
    # Build example usage
    example_usage = []
    for sug in suggestions[:3]:  # Top 3 suggestions
        tool_name = sug["tool"]
        params = sug["parameters"]
        example_usage.append(f"Call '{tool_name}' with parameters: {params}")
    
    return {
        "interpreted_intent": intent,
        "query": query,
        "suggested_tools": suggestions[:max_results],
        "reasoning": reasoning,
        "example_usage": example_usage,
        "note": "Parameters marked with <extract from query> need to be filled in based on query context"
    }


async def signal_summarize(
    session_manager: SessionManager,
    session_id: str,
    variable_path: str,
    max_changes: Optional[int] = 20,
    include_stats: Optional[bool] = True
) -> Dict[str, Any]:
    """
    Generate a concise summary of signal behavior for LLM context efficiency.
    
    Instead of returning all signal changes, provides a high-level summary
    that fits efficiently in LLM context windows.
    
    Args:
        session_id: Active waveform session ID
        variable_path: Path to variable (e.g., "top.cpu.state")
        max_changes: Maximum number of representative changes to include
        include_stats: Whether to include statistical analysis
        
    Returns:
        Dictionary containing:
        - signal_name: Signal name and path
        - summary: One-line description of behavior
        - statistics: Toggle count, value range, activity
        - representative_changes: Key transitions (not all changes)
        - patterns: Detected patterns (periodic, constant, etc.)
        - recommendations: Suggested next steps for analysis
        
    Example output:
        "Signal 'clk' toggles 1000 times, periodic with 10ns period.
         Stays high 50% of time. Likely a clock signal."
    """
    session = session_manager.get_session(session_id)
    
    # Get signal changes using the waveform API directly
    waveform = session.waveform
    hierarchy = session.hierarchy
    var = hierarchy.get_var_by_name(variable_path)
    if not var:
        raise QueryError("VARIABLE_NOT_FOUND", f"Variable '{variable_path}' not found")
    
    # Get all changes (analyze up to 1000)
    changes = []
    limit_count = min(1000, limit=1000) if hasattr(var, 'changes') else 1000
    for i, change in enumerate(waveform.get_signal_values(var)):
        if i >= limit_count:
            break
        changes.append({
            "time": change.time,
            "value": str(change.value)
        })
    
    total_changes = len(changes)
    
    # Basic info
    summary_data = {
        "signal_name": variable_path,
        "total_changes": total_changes,
        "statistics": {},
        "representative_changes": [],
        "patterns": [],
        "recommendations": []
    }
    
    if total_changes == 0:
        summary_data["summary"] = f"Signal '{variable_path}' has no transitions (constant value)"
        summary_data["patterns"].append("constant")
        return summary_data
    
    # Statistics
    if include_stats:
        times = [c["time"] for c in changes]
        min_time = min(times)
        max_time = max(times)
        duration = max_time - min_time if max_time > min_time else 1
        
        # Value analysis
        values = [c["value"] for c in changes]
        unique_values = set(values)
        
        # Toggle analysis (for 1-bit signals)
        if all(v in ['0', '1', 'x', 'z'] for v in unique_values):
            toggle_count = sum(1 for i in range(1, len(values)) if values[i] != values[i-1])
            summary_data["statistics"]["toggle_count"] = toggle_count
            summary_data["statistics"]["toggle_rate"] = toggle_count / duration if duration > 0 else 0
        
        summary_data["statistics"]["unique_values"] = len(unique_values)
        summary_data["statistics"]["time_range"] = {"start": min_time, "end": max_time}
        summary_data["statistics"]["duration"] = duration
        
        # Periodicity detection (simple)
        if len(changes) >= 4:
            intervals = [times[i+1] - times[i] for i in range(min(len(times)-1, 10))]
            avg_interval = sum(intervals) / len(intervals)
            interval_variance = sum((t - avg_interval)**2 for t in intervals) / len(intervals)
            
            if interval_variance < avg_interval * 0.1:  # Low variance = periodic
                summary_data["patterns"].append("periodic")
                summary_data["statistics"]["period"] = avg_interval
    
    # Representative changes (evenly sampled)
    if max_changes and total_changes > max_changes:
        step = total_changes // max_changes
        representative = [changes[i*step] for i in range(max_changes)]
        summary_data["representative_changes"] = representative
        summary_data["truncated"] = True
    else:
        summary_data["representative_changes"] = changes
        summary_data["truncated"] = False
    
    # Pattern detection
    if total_changes == 1:
        summary_data["patterns"].append("single_transition")
    elif total_changes < 5:
        summary_data["patterns"].append("low_activity")
    elif "toggle_count" in summary_data["statistics"]:
        toggle_rate = summary_data["statistics"]["toggle_rate"]
        if toggle_rate > 0.1:  # High activity
            summary_data["patterns"].append("high_activity")
            summary_data["patterns"].append("likely_clock")
        elif toggle_rate < 0.001:
            summary_data["patterns"].append("low_activity")
    
    # Value pattern detection
    if "unique_values" in summary_data["statistics"]:
        if summary_data["statistics"]["unique_values"] == 1:
            summary_data["patterns"].append("constant_after_first_change")
        elif summary_data["statistics"]["unique_values"] == 2:
            summary_data["patterns"].append("binary_toggle")
    
    # Generate summary text
    summary_parts = []
    summary_parts.append(f"Signal '{variable_path}' has {total_changes} transitions")
    
    if "period" in summary_data["statistics"]:
        period = summary_data["statistics"]["period"]
        summary_parts.append(f"periodic with period ~{period:.2f} time units")
    
    if "toggle_count" in summary_data["statistics"]:
        toggle_count = summary_data["statistics"]["toggle_count"]
        summary_parts.append(f"{toggle_count} toggles")
    
    if "likely_clock" in summary_data["patterns"]:
        summary_parts.append("(likely a clock signal)")
    elif "constant" in summary_data["patterns"]:
        summary_parts.append("(constant value)")
    elif "low_activity" in summary_data["patterns"]:
        summary_parts.append("(low activity - control signal or static)")
    
    summary_data["summary"] = ". ".join(summary_parts)
    
    # Recommendations
    if "likely_clock" in summary_data["patterns"]:
        summary_data["recommendations"].append("Use this signal for temporal reference")
        summary_data["recommendations"].append("Consider using debug_event_timeline with this clock")
    elif "low_activity" in summary_data["patterns"]:
        summary_data["recommendations"].append("Check if this is a control or enable signal")
        summary_data["recommendations"].append("Use debug_trace_causality to find what triggers changes")
    elif "constant" in summary_data["patterns"]:
        summary_data["recommendations"].append("Signal never changes - may indicate unused or tied signal")
    else:
        summary_data["recommendations"].append("Use signal_list_changes for detailed transition history")
        summary_data["recommendations"].append("Use debug_find_transition to find specific conditions")
    
    return summary_data


async def recommend_related_signals(
    session_manager: SessionManager,
    session_id: str,
    variable_path: str,
    max_recommendations: Optional[int] = 10
) -> Dict[str, Any]:
    """
    Recommend signals related to the given signal for deeper analysis.
    
    Helps LLMs discover relevant signals without exploring entire hierarchy.
    Uses heuristics based on naming, scope, and activity patterns.
    
    Args:
        session_id: Active waveform session ID
        variable_path: Path to reference signal
        max_recommendations: Maximum number of recommendations
        
    Returns:
        Dictionary containing:
        - reference_signal: The input signal
        - recommendations: List of related signals with relevance scores
        - categories: Grouped by relationship type (same scope, similar name, etc.)
        - reasoning: Why each signal is recommended
        
    Relationship types:
        - same_scope: Signals in same module/scope (high relevance)
        - similar_name: Signals with similar naming patterns
        - complementary: Related by common patterns (clk/data, req/ack)
        - control_flow: Enable, valid, ready signals
    """
    from .tools_hierarchy import hierarchy_get_scope
    
    session = session_manager.get_session(session_id)
    
    # Parse the path to get scope and signal name
    path_parts = variable_path.split('.')
    signal_name = path_parts[-1]
    scope_path = '.'.join(path_parts[:-1]) if len(path_parts) > 1 else None
    
    recommendations = []
    categories = {
        "same_scope": [],
        "similar_name": [],
        "complementary": [],
        "control_flow": []
    }
    
    # Get signals in same scope (highest relevance)
    if scope_path:
        try:
            scope_data = await hierarchy_get_scope(
                session_id=session_id,
                scope_path=scope_path,
                include_variables=True,
                include_child_scopes=False
            )
            
            for var in scope_data.get("variables", [])[:50]:  # Limit to 50
                var_name = var["name"]
                if var_name == signal_name:
                    continue
                
                rec = {
                    "path": f"{scope_path}.{var_name}" if scope_path else var_name,
                    "name": var_name,
                    "relevance": 0.8,
                    "reason": "In same scope",
                    "category": "same_scope"
                }
                categories["same_scope"].append(rec)
        except Exception:
            pass  # Scope not found or error
    
    # Similar names (substring matching)
    signal_lower = signal_name.lower()
    base_name = signal_lower.rstrip('0123456789_')  # Remove trailing numbers/underscores
    
    # Common complementary patterns
    complementary_patterns = {
        'clk': ['data', 'valid', 'enable', 'en'],
        'clock': ['data', 'valid', 'enable'],
        'req': ['ack', 'grant', 'gnt', 'ready'],
        'request': ['acknowledge', 'grant', 'ready'],
        'valid': ['ready', 'data'],
        'enable': ['data', 'out', 'output'],
        'en': ['data', 'out'],
        'write': ['read', 'data', 'addr', 'address'],
        'wr': ['rd', 'data', 'addr'],
        'read': ['write', 'data', 'addr', 'address'],
        'rd': ['wr', 'data', 'addr']
    }
    
    # Check for complementary signals
    for pattern, complements in complementary_patterns.items():
        if pattern in signal_lower:
            for comp in complements:
                # These are hypothetical - would need hierarchy search
                rec = {
                    "pattern": f"*{comp}*",
                    "relevance": 0.7,
                    "reason": f"Complementary to {pattern} signal",
                    "category": "complementary",
                    "note": f"Search for signals matching pattern '*{comp}*' in hierarchy"
                }
                categories["complementary"].append(rec)
                break  # One suggestion per pattern
            break
    
    # Control flow signals
    control_keywords = ['valid', 'ready', 'enable', 'en', 'start', 'stop', 'reset', 'rst']
    if not any(kw in signal_lower for kw in control_keywords):
        for kw in control_keywords:
            rec = {
                "pattern": f"*{kw}*",
                "relevance": 0.6,
                "reason": "Common control signal",
                "category": "control_flow",
                "note": f"Search for signals matching pattern '*{kw}*' in scope"
            }
            categories["control_flow"].append(rec)
            if len(categories["control_flow"]) >= 3:  # Limit suggestions
                break
    
    # Compile top recommendations
    all_recs = (
        categories["same_scope"][:5] +
        categories["complementary"][:3] +
        categories["control_flow"][:2]
    )
    
    # Sort by relevance
    all_recs.sort(key=lambda x: x["relevance"], reverse=True)
    recommendations = all_recs[:max_recommendations]
    
    return {
        "reference_signal": variable_path,
        "recommendations": recommendations,
        "categories": {
            k: v for k, v in categories.items() if v  # Only non-empty categories
        },
        "total_recommendations": len(recommendations),
        "note": "Some recommendations are patterns to search for, not direct signal paths"
    }


async def docs_get_started() -> Dict[str, Any]:
    """
    Get started guide for using the PyWellen MCP server.
    
    Provides quick-start information for LLMs to understand available tools
    and common workflows.
    
    Returns:
        Dictionary containing:
        - overview: Brief description of the server
        - quick_start: Step-by-step getting started guide
        - common_workflows: Example task sequences
        - tool_categories: Tools organized by purpose
        - tips: Best practices for LLM interaction
    """
    return {
        "overview": {
            "name": "PyWellen MCP Server",
            "purpose": "Waveform analysis for VCD, FST, and GHW files",
            "capabilities": [
                "Open and inspect waveform files",
                "Navigate design hierarchy",
                "Query signal values and changes",
                "Debug with causality tracing and transition finding",
                "Compare signals and analyze patterns",
                "Format values and perform batch operations"
            ]
        },
        "quick_start": {
            "step1": {
                "action": "Open a waveform file",
                "tool": "waveform_open",
                "parameters": {"file_path": "/path/to/file.vcd"},
                "returns": "session_id for subsequent operations"
            },
            "step2": {
                "action": "Get waveform metadata",
                "tool": "waveform_info",
                "parameters": {"session_id": "<from step1>"},
                "returns": "format, timescale, scope/signal counts"
            },
            "step3": {
                "action": "Explore hierarchy",
                "tool": "hierarchy_list_top_scopes",
                "parameters": {"session_id": "<from step1>"},
                "returns": "top-level design modules"
            },
            "step4": {
                "action": "Find signals of interest",
                "tool": "hierarchy_search",
                "parameters": {"session_id": "<from step1>", "pattern": "clk"},
                "returns": "matching signals"
            },
            "step5": {
                "action": "Analyze signal behavior",
                "tool": "signal_summarize",
                "parameters": {"session_id": "<from step1>", "variable_path": "top.clk"},
                "returns": "concise summary of signal activity"
            }
        },
        "common_workflows": {
            "debugging": [
                "1. Open waveform with waveform_open",
                "2. Find error signal with hierarchy_search",
                "3. Get value at failure time with signal_get_value",
                "4. Trace causes with debug_trace_causality",
                "5. Build timeline with debug_event_timeline"
            ],
            "clock_analysis": [
                "1. Find clocks with search_by_activity (high toggles)",
                "2. Or search with hierarchy_search pattern='clk'",
                "3. Summarize behavior with signal_summarize",
                "4. Find edges with debug_find_transition condition='rises'"
            ],
            "signal_comparison": [
                "1. Find signals to compare (hierarchy_search)",
                "2. Compare with signal_compare",
                "3. If differences found, get specific values",
                "4. Build event timeline for both signals"
            ],
            "design_exploration": [
                "1. Get metadata with waveform_info",
                "2. List top scopes with hierarchy_list_top_scopes",
                "3. Drill down with hierarchy_get_scope",
                "4. List variables with hierarchy_list_variables",
                "5. Use recommend_related_signals for discovery"
            ]
        },
        "tool_categories": {
            "session_management": [
                "waveform_open", "waveform_close", "waveform_info", "waveform_list_sessions"
            ],
            "hierarchy_navigation": [
                "hierarchy_list_top_scopes", "hierarchy_get_scope",
                "hierarchy_list_variables", "hierarchy_search"
            ],
            "signal_analysis": [
                "signal_get_value", "signal_list_changes", "signal_get_at_time",
                "signal_summarize", "signal_compare"
            ],
            "debugging": [
                "debug_find_transition", "debug_trace_causality",
                "debug_event_timeline", "search_by_activity"
            ],
            "formatting": [
                "format_value", "format_as_signed"
            ],
            "batch_operations": [
                "batch_get_values", "batch_compare_signals"
            ],
            "llm_optimization": [
                "query_natural_language", "signal_summarize",
                "recommend_related_signals", "docs_get_started"
            ]
        },
        "tips": [
            "Always start by opening a waveform with waveform_open",
            "Use signal_summarize instead of signal_list_changes for concise info",
            "Use query_natural_language to interpret ambiguous user requests",
            "Use recommend_related_signals to discover related signals",
            "Close sessions with waveform_close when done to free resources",
            "Use batch operations for multiple signals to reduce round trips",
            "Session IDs expire after 1 hour of inactivity"
        ],
        "note": "For detailed tool schemas, use the MCP list_tools command"
    }


async def docs_tool_guide(tool_name: str) -> Dict[str, Any]:
    """
    Get detailed usage guide for a specific tool.
    
    Provides comprehensive documentation for how to use a particular tool,
    including parameters, return values, and examples.
    
    Args:
        tool_name: Name of the tool to get documentation for
        
    Returns:
        Dictionary containing:
        - tool_name: Name of the tool
        - description: What the tool does
        - parameters: Detailed parameter descriptions
        - returns: What the tool returns
        - examples: Usage examples
        - related_tools: Other tools commonly used with this one
        - common_errors: Typical errors and solutions
    """
    # Tool documentation database
    tool_docs = {
        "waveform_open": {
            "description": "Open a waveform file (VCD, FST, or GHW) and create a new session",
            "parameters": {
                "file_path": "Path to waveform file",
                "multi_threaded": "Enable parallel processing (default: false)",
                "remove_empty_scopes": "Remove empty hierarchy scopes (default: true)"
            },
            "returns": "session_id (string), format, timescale, metadata",
            "examples": [
                'waveform_open(file_path="/path/to/design.vcd")',
                'waveform_open(file_path="sim.fst", multi_threaded=true)'
            ],
            "related_tools": ["waveform_info", "waveform_close", "hierarchy_list_top_scopes"],
            "common_errors": [
                "File not found: Check path is absolute and file exists",
                "Unsupported format: Only VCD, FST, GHW supported",
                "Max sessions reached: Close unused sessions first"
            ]
        },
        "signal_get_value": {
            "description": "Get signal value at a specific time",
            "parameters": {
                "session_id": "Active session ID",
                "variable_path": "Signal path (e.g., 'top.cpu.state')",
                "time": "Time point or 'current' for last value"
            },
            "returns": "value, time, formatted values in multiple bases",
            "examples": [
                'signal_get_value(session_id="...", variable_path="top.clk", time=1000)',
                'signal_get_value(session_id="...", variable_path="top.data", time="current")'
            ],
            "related_tools": ["signal_list_changes", "signal_get_at_time", "format_value"],
            "common_errors": [
                "Variable not found: Check path is correct",
                "Invalid time: Must be within waveform time range"
            ]
        },
        "debug_trace_causality": {
            "description": "Find potential causes of a signal change",
            "parameters": {
                "session_id": "Active session ID",
                "target_path": "Signal that changed",
                "target_time": "When the change occurred",
                "search_window": "How far back to search (default: 500)",
                "signal_paths": "Optional specific signals to check"
            },
            "returns": "List of potential causes with relevance scores (0-1)",
            "examples": [
                'debug_trace_causality(session_id="...", target_path="top.error", target_time=5000)',
                'debug_trace_causality(..., search_window=1000, signal_paths=["top.en", "top.valid"])'
            ],
            "related_tools": ["debug_event_timeline", "debug_find_transition", "recommend_related_signals"],
            "common_errors": [
                "No causes found: Try larger search_window",
                "Too many signals: Use signal_paths to limit scope"
            ]
        },
        "signal_summarize": {
            "description": "Get concise summary of signal behavior (LLM-optimized)",
            "parameters": {
                "session_id": "Active session ID",
                "variable_path": "Signal to summarize",
                "max_changes": "Representative changes to include (default: 20)",
                "include_stats": "Include statistical analysis (default: true)"
            },
            "returns": "Summary text, statistics, patterns, recommendations",
            "examples": [
                'signal_summarize(session_id="...", variable_path="top.clk")',
                'signal_summarize(..., max_changes=10, include_stats=true)'
            ],
            "related_tools": ["signal_list_changes", "search_by_activity", "recommend_related_signals"],
            "common_errors": [
                "No changes: Signal is constant",
                "Too many changes: Reduce max_changes for shorter output"
            ]
        }
    }
    
    if tool_name not in tool_docs:
        # Return generic response for undocumented tools
        return {
            "tool_name": tool_name,
            "status": "not_documented",
            "note": f"Detailed documentation for '{tool_name}' not yet available",
            "suggestion": "Use MCP list_tools to see tool schema, or try docs_get_started for overview"
        }
    
    doc = tool_docs[tool_name]
    return {
        "tool_name": tool_name,
        "description": doc["description"],
        "parameters": doc["parameters"],
        "returns": doc["returns"],
        "examples": doc["examples"],
        "related_tools": doc["related_tools"],
        "common_errors": doc["common_errors"]
    }
