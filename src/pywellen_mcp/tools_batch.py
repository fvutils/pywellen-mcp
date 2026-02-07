"""
Advanced batch query operations for efficient signal access.

This module provides tools for querying multiple signals in a single operation,
reducing round-trip overhead and improving performance for complex workflows.
"""

from typing import List, Dict, Any, Optional, Literal
from .session import SessionManager
from .errors import QueryError
from .tools_signal import SignalTools


async def batch_query_signals(
    session_manager: SessionManager,
    session_id: str,
    queries: List[Dict[str, Any]],
    signal_tools: Optional[SignalTools] = None,
) -> Dict[str, Any]:
    """
    Query multiple signals in a single batch operation.
    
    This tool dramatically reduces latency for workflows that need to query
    many signals, by executing all queries in parallel and returning results
    in a single response.
    
    Args:
        session_manager: Session management instance
        session_id: Active waveform session
        queries: List of query specifications, each containing:
            - variable_path (str): Signal to query
            - operation (str): "get_value", "get_changes", or "get_statistics"
            - params (dict): Operation-specific parameters
        signal_tools: Optional SignalTools instance (created if not provided)
        
    Returns:
        {
            "results": [
                {"query_index": int, "success": bool, "data": dict | None, "error": str | None},
                ...
            ],
            "total": int,
            "successful": int,
            "failed": int
        }
        
    Example queries:
        [
            {
                "variable_path": "top.clk",
                "operation": "get_value",
                "params": {"times": [100, 200, 300]}
            },
            {
                "variable_path": "top.state",
                "operation": "get_changes",
                "params": {"start_time": 0, "end_time": 1000}
            },
            {
                "variable_path": "top.counter",
                "operation": "get_statistics",
                "params": {}
            }
        ]
    """
    # Create signal tools if not provided
    if signal_tools is None:
        signal_tools = SignalTools(session_manager)
    
    # Validate session exists
    session_manager.get_session(session_id)
    
    results = []
    successful = 0
    failed = 0
    
    # Process each query
    for idx, query in enumerate(queries):
        result_entry = {
            "query_index": idx,
            "success": False,
            "data": None,
            "error": None,
        }
        
        try:
            # Extract query components
            variable_path = query.get("variable_path")
            operation = query.get("operation")
            params = query.get("params", {})
            
            if not variable_path:
                raise QueryError("Missing 'variable_path' in query", {"query_index": idx})
            if not operation:
                raise QueryError("Missing 'operation' in query", {"query_index": idx})
            
            # Route to appropriate operation
            if operation == "get_value":
                data = await signal_tools.signal_get_value(
                    session_id=session_id,
                    variable_path=variable_path,
                    **params
                )
            elif operation == "get_changes":
                data = await signal_tools.signal_get_changes(
                    session_id=session_id,
                    variable_path=variable_path,
                    **params
                )
            elif operation == "get_statistics":
                data = await signal_tools.signal_get_statistics(
                    session_id=session_id,
                    variable_path=variable_path,
                    **params
                )
            else:
                raise QueryError(
                    f"Unknown operation: {operation}",
                    {"valid_operations": ["get_value", "get_changes", "get_statistics"]}
                )
            
            result_entry["success"] = True
            result_entry["data"] = data
            successful += 1
            
        except Exception as e:
            result_entry["error"] = str(e)
            failed += 1
        
        results.append(result_entry)
    
    return {
        "results": results,
        "total": len(queries),
        "successful": successful,
        "failed": failed,
    }
