"""
Export and integration tools for PyWellen MCP server.

This module provides tools for exporting waveform data and integrating
with external tools and workflows.
"""

import csv
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from .session import SessionManager
from .errors import SessionError, QueryError, FileError


async def export_to_csv(
    session_manager: SessionManager,
    session_id: str,
    signal_paths: List[str],
    output_path: str,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    include_header: Optional[bool] = True,
    time_format: Optional[str] = "absolute"
) -> Dict[str, Any]:
    """
    Export signal data to CSV format.
    
    Creates a CSV file with time in the first column and signal values
    in subsequent columns. Useful for analysis in spreadsheets or data tools.
    
    Args:
        session_id: Active waveform session ID
        signal_paths: List of signal paths to export
        output_path: Path to output CSV file
        start_time: Optional start time for export range
        end_time: Optional end time for export range
        include_header: Include column headers (default: true)
        time_format: Time format - "absolute" or "relative" (default: absolute)
        
    Returns:
        Dictionary containing:
        - output_file: Path to created CSV file
        - signals_exported: Number of signals exported
        - rows_written: Number of data rows written
        - time_range: Actual time range exported
        - format: CSV format details
        
    Example:
        export_to_csv(
            session_id="abc123",
            signal_paths=["top.clk", "top.data", "top.valid"],
            output_path="/tmp/signals.csv"
        )
    """
    session = session_manager.get_session(session_id)
    
    # Validate output path
    output_path = os.path.abspath(output_path)
    output_dir = os.path.dirname(output_path)
    
    if not os.path.exists(output_dir):
        raise FileError("INVALID_PATH", f"Output directory does not exist: {output_dir}")
    
    if not os.access(output_dir, os.W_OK):
        raise FileError("PERMISSION_DENIED", f"Cannot write to directory: {output_dir}")
    
    # Get time range from waveform
    time_table = session.time_table
    if time_table:
        waveform_start = time_table.start_time()
        waveform_end = time_table.end_time()
    else:
        waveform_start = 0
        waveform_end = 0
    
    # Apply time filtering
    export_start = start_time if start_time is not None else waveform_start
    export_end = end_time if end_time is not None else waveform_end
    
    # Validate signal paths and get variables
    hierarchy = session.hierarchy
    variables = []
    for path in signal_paths:
        var = hierarchy.get_var_by_name(path)
        if not var:
            raise QueryError("VARIABLE_NOT_FOUND", f"Variable '{path}' not found")
        variables.append((path, var))
    
    # Collect all unique time points across all signals
    time_points = set()
    waveform = session.waveform
    
    for _, var in variables:
        for change in waveform.get_signal_values(var):
            t = change.time
            if export_start <= t <= export_end:
                time_points.add(t)
    
    # Sort time points
    sorted_times = sorted(time_points)
    
    if not sorted_times:
        raise QueryError("NO_DATA", "No signal changes in specified time range")
    
    # Build data table
    rows_written = 0
    
    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        if include_header:
            if time_format == "relative":
                header = ["Time (relative)"] + signal_paths
            else:
                header = ["Time"] + signal_paths
            writer.writerow(header)
        
        # Track current value for each signal
        current_values = {}
        for path, var in variables:
            current_values[path] = "x"  # Initial value unknown
        
        # Get initial values before export_start
        for path, var in variables:
            last_value = "x"
            for change in waveform.get_signal_values(var):
                if change.time <= export_start:
                    last_value = str(change.value)
                else:
                    break
            current_values[path] = last_value
        
        # Write data rows
        base_time = sorted_times[0] if time_format == "relative" else 0
        
        for time_point in sorted_times:
            # Update values for signals that changed at this time
            for path, var in variables:
                for change in waveform.get_signal_values(var):
                    if change.time == time_point:
                        current_values[path] = str(change.value)
                        break
            
            # Write row
            if time_format == "relative":
                time_col = time_point - base_time
            else:
                time_col = time_point
            
            row = [time_col] + [current_values[path] for path in signal_paths]
            writer.writerow(row)
            rows_written += 1
    
    return {
        "output_file": output_path,
        "signals_exported": len(signal_paths),
        "rows_written": rows_written,
        "time_range": {
            "start": sorted_times[0],
            "end": sorted_times[-1],
            "duration": sorted_times[-1] - sorted_times[0]
        },
        "format": {
            "type": "csv",
            "delimiter": ",",
            "header_included": include_header,
            "time_format": time_format
        }
    }


async def export_hierarchy_tree(
    session_manager: SessionManager,
    session_id: str,
    output_path: str,
    format: Optional[str] = "json",
    include_variables: Optional[bool] = True,
    include_metadata: Optional[bool] = True,
    max_depth: Optional[int] = None
) -> Dict[str, Any]:
    """
    Export design hierarchy as a tree structure.
    
    Creates a structured representation of the design hierarchy
    suitable for visualization or external processing.
    
    Args:
        session_id: Active waveform session ID
        output_path: Path to output file
        format: Output format - "json", "yaml", or "text" (default: json)
        include_variables: Include variable details (default: true)
        include_metadata: Include scope metadata (default: true)
        max_depth: Maximum tree depth (None = unlimited)
        
    Returns:
        Dictionary containing:
        - output_file: Path to created file
        - format: Output format used
        - total_scopes: Number of scopes exported
        - total_variables: Number of variables exported
        - max_depth_reached: Maximum depth in hierarchy
        
    Example:
        export_hierarchy_tree(
            session_id="abc123",
            output_path="/tmp/hierarchy.json",
            format="json"
        )
    """
    session = session_manager.get_session(session_id)
    hierarchy = session.hierarchy
    
    # Validate output path
    output_path = os.path.abspath(output_path)
    output_dir = os.path.dirname(output_path)
    
    if not os.path.exists(output_dir):
        raise FileError("INVALID_PATH", f"Output directory does not exist: {output_dir}")
    
    if not os.access(output_dir, os.W_OK):
        raise FileError("PERMISSION_DENIED", f"Cannot write to directory: {output_dir}")
    
    # Validate format
    if format not in ["json", "yaml", "text"]:
        raise QueryError("INVALID_FORMAT", f"Unsupported format: {format}")
    
    # Build hierarchy tree
    def build_scope_tree(scope, current_depth=0):
        """Recursively build hierarchy tree."""
        if max_depth is not None and current_depth >= max_depth:
            return None
        
        scope_data = {
            "name": scope.name,
            "type": str(scope.scope_type)
        }
        
        if include_metadata:
            scope_data["metadata"] = {
                "num_children": len(list(scope.children())),
                "num_variables": len(list(scope.variables())) if include_variables else 0,
                "depth": current_depth
            }
        
        # Add variables
        if include_variables:
            variables = []
            for var in scope.variables():
                var_data = {
                    "name": var.name,
                    "type": str(var.var_type),
                    "direction": str(var.direction) if hasattr(var, 'direction') else None,
                    "length": var.length()
                }
                variables.append(var_data)
            
            if variables:
                scope_data["variables"] = variables
        
        # Add child scopes
        children = []
        for child in scope.children():
            child_tree = build_scope_tree(child, current_depth + 1)
            if child_tree:
                children.append(child_tree)
        
        if children:
            scope_data["children"] = children
        
        return scope_data
    
    # Build tree from top-level scopes
    tree_data = {
        "design": session.waveform.file_name() if hasattr(session.waveform, 'file_name') else "unknown",
        "scopes": []
    }
    
    total_scopes = 0
    total_variables = 0
    max_depth_reached = 0
    
    for top_scope in hierarchy.top_scopes():
        scope_tree = build_scope_tree(top_scope, 0)
        if scope_tree:
            tree_data["scopes"].append(scope_tree)
            
            # Count scopes and variables recursively
            def count_tree(node, depth=0):
                nonlocal total_scopes, total_variables, max_depth_reached
                total_scopes += 1
                max_depth_reached = max(max_depth_reached, depth)
                
                if "variables" in node:
                    total_variables += len(node["variables"])
                
                if "children" in node:
                    for child in node["children"]:
                        count_tree(child, depth + 1)
            
            count_tree(scope_tree, 0)
    
    # Write output file based on format
    if format == "json":
        with open(output_path, 'w') as f:
            json.dump(tree_data, f, indent=2)
    
    elif format == "yaml":
        try:
            import yaml
            with open(output_path, 'w') as f:
                yaml.dump(tree_data, f, default_flow_style=False, sort_keys=False)
        except ImportError:
            raise FileError("MISSING_DEPENDENCY", "YAML support requires 'pyyaml' package")
    
    elif format == "text":
        # Text tree format
        with open(output_path, 'w') as f:
            def write_tree(node, indent=0):
                prefix = "  " * indent
                f.write(f"{prefix}├─ {node['name']} ({node['type']})\n")
                
                if "variables" in node:
                    for var in node["variables"]:
                        f.write(f"{prefix}  │  {var['name']} : {var['type']}\n")
                
                if "children" in node:
                    for child in node["children"]:
                        write_tree(child, indent + 1)
            
            f.write(f"Design: {tree_data['design']}\n\n")
            for scope in tree_data["scopes"]:
                write_tree(scope, 0)
    
    return {
        "output_file": output_path,
        "format": format,
        "total_scopes": total_scopes,
        "total_variables": total_variables,
        "max_depth_reached": max_depth_reached,
        "file_size": os.path.getsize(output_path)
    }


async def load_signal_list(
    session_manager: SessionManager,
    session_id: str,
    config_path: str
) -> Dict[str, Any]:
    """
    Load signal list from configuration file.
    
    Supports JSON and YAML configuration files defining signal groups,
    filters, and preferences for analysis workflows.
    
    Args:
        session_id: Active waveform session ID
        config_path: Path to configuration file (.json or .yaml)
        
    Returns:
        Dictionary containing:
        - signals: List of signal paths loaded
        - groups: Signal groups defined in config
        - filters: Filters applied
        - metadata: Additional configuration metadata
        
    Config file format (JSON):
        {
            "signals": ["top.clk", "top.data"],
            "groups": {
                "control": ["top.valid", "top.ready"],
                "data": ["top.data", "top.addr"]
            },
            "filters": {
                "scope": "top.cpu",
                "types": ["Wire", "Reg"]
            }
        }
    
    Example:
        load_signal_list(
            session_id="abc123",
            config_path="/path/to/signals.json"
        )
    """
    session = session_manager.get_session(session_id)
    
    # Validate file exists
    if not os.path.exists(config_path):
        raise FileError("FILE_NOT_FOUND", f"Configuration file not found: {config_path}")
    
    if not os.access(config_path, os.R_OK):
        raise FileError("PERMISSION_DENIED", f"Cannot read file: {config_path}")
    
    # Determine format from extension
    ext = os.path.splitext(config_path)[1].lower()
    
    try:
        if ext == ".json":
            with open(config_path, 'r') as f:
                config = json.load(f)
        
        elif ext in [".yaml", ".yml"]:
            try:
                import yaml
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
            except ImportError:
                raise FileError("MISSING_DEPENDENCY", "YAML support requires 'pyyaml' package")
        
        else:
            raise FileError("UNSUPPORTED_FORMAT", f"Unsupported file format: {ext}")
    
    except json.JSONDecodeError as e:
        raise FileError("PARSE_ERROR", f"Invalid JSON: {e}")
    except Exception as e:
        raise FileError("PARSE_ERROR", f"Failed to parse config: {e}")
    
    # Extract signals
    signals = config.get("signals", [])
    groups = config.get("groups", {})
    filters = config.get("filters", {})
    metadata = config.get("metadata", {})
    
    # Validate signals exist
    hierarchy = session.hierarchy
    validated_signals = []
    invalid_signals = []
    
    for signal_path in signals:
        var = hierarchy.get_var_by_name(signal_path)
        if var:
            validated_signals.append(signal_path)
        else:
            invalid_signals.append(signal_path)
    
    # Validate group signals
    validated_groups = {}
    for group_name, group_signals in groups.items():
        valid_group_signals = []
        for signal_path in group_signals:
            var = hierarchy.get_var_by_name(signal_path)
            if var:
                valid_group_signals.append(signal_path)
            else:
                invalid_signals.append(signal_path)
        
        validated_groups[group_name] = valid_group_signals
    
    return {
        "config_file": config_path,
        "signals": validated_signals,
        "groups": validated_groups,
        "filters": filters,
        "metadata": metadata,
        "validation": {
            "total_signals": len(signals) + sum(len(g) for g in groups.values()),
            "valid_signals": len(validated_signals) + sum(len(g) for g in validated_groups.values()),
            "invalid_signals": invalid_signals if invalid_signals else None
        }
    }


async def save_signal_list(
    session_manager: SessionManager,
    session_id: str,
    output_path: str,
    signal_paths: List[str],
    groups: Optional[Dict[str, List[str]]] = None,
    filters: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    format: Optional[str] = "json"
) -> Dict[str, Any]:
    """
    Save signal list to configuration file.
    
    Creates a reusable configuration file for signal analysis workflows.
    
    Args:
        session_id: Active waveform session ID
        output_path: Path to output configuration file
        signal_paths: List of signal paths to save
        groups: Optional signal groups dictionary
        filters: Optional filter configuration
        metadata: Optional metadata dictionary
        format: Output format - "json" or "yaml" (default: json)
        
    Returns:
        Dictionary containing:
        - output_file: Path to created file
        - format: Format used
        - signals_saved: Number of signals saved
        - groups_saved: Number of groups saved
        
    Example:
        save_signal_list(
            session_id="abc123",
            output_path="/tmp/signals.json",
            signal_paths=["top.clk", "top.data"],
            groups={"control": ["top.valid", "top.ready"]}
        )
    """
    session = session_manager.get_session(session_id)
    
    # Validate output path
    output_path = os.path.abspath(output_path)
    output_dir = os.path.dirname(output_path)
    
    if not os.path.exists(output_dir):
        raise FileError("INVALID_PATH", f"Output directory does not exist: {output_dir}")
    
    if not os.access(output_dir, os.W_OK):
        raise FileError("PERMISSION_DENIED", f"Cannot write to directory: {output_dir}")
    
    # Validate signals exist
    hierarchy = session.hierarchy
    for signal_path in signal_paths:
        var = hierarchy.get_var_by_name(signal_path)
        if not var:
            raise QueryError("VARIABLE_NOT_FOUND", f"Variable '{signal_path}' not found")
    
    # Build configuration
    config = {
        "signals": signal_paths
    }
    
    if groups:
        config["groups"] = groups
    
    if filters:
        config["filters"] = filters
    
    if metadata:
        config["metadata"] = metadata
    else:
        # Add default metadata
        config["metadata"] = {
            "created_by": "pywellen-mcp",
            "session_id": session_id
        }
    
    # Write file
    if format == "json":
        with open(output_path, 'w') as f:
            json.dump(config, f, indent=2)
    
    elif format == "yaml":
        try:
            import yaml
            with open(output_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        except ImportError:
            raise FileError("MISSING_DEPENDENCY", "YAML support requires 'pyyaml' package")
    
    else:
        raise QueryError("INVALID_FORMAT", f"Unsupported format: {format}")
    
    return {
        "output_file": output_path,
        "format": format,
        "signals_saved": len(signal_paths),
        "groups_saved": len(groups) if groups else 0,
        "file_size": os.path.getsize(output_path)
    }


async def export_signal_data(
    session_manager: SessionManager,
    session_id: str,
    signal_path: str,
    output_path: str,
    format: Optional[str] = "json",
    start_time: Optional[int] = None,
    end_time: Optional[int] = None
) -> Dict[str, Any]:
    """
    Export single signal data to JSON or other formats.
    
    Exports all changes for a single signal with timestamps and values.
    
    Args:
        session_id: Active waveform session ID
        signal_path: Signal path to export
        output_path: Path to output file
        format: Output format - "json" or "csv" (default: json)
        start_time: Optional start time for export range
        end_time: Optional end time for export range
        
    Returns:
        Dictionary containing:
        - output_file: Path to created file
        - signal_path: Signal that was exported
        - changes_exported: Number of changes written
        - time_range: Time range exported
        
    Example:
        export_signal_data(
            session_id="abc123",
            signal_path="top.clk",
            output_path="/tmp/clk_data.json"
        )
    """
    session = session_manager.get_session(session_id)
    hierarchy = session.hierarchy
    
    # Validate signal
    var = hierarchy.get_var_by_name(signal_path)
    if not var:
        raise QueryError("VARIABLE_NOT_FOUND", f"Variable '{signal_path}' not found")
    
    # Validate output path
    output_path = os.path.abspath(output_path)
    output_dir = os.path.dirname(output_path)
    
    if not os.path.exists(output_dir):
        raise FileError("INVALID_PATH", f"Output directory does not exist: {output_dir}")
    
    if not os.access(output_dir, os.W_OK):
        raise FileError("PERMISSION_DENIED", f"Cannot write to directory: {output_dir}")
    
    # Collect changes
    waveform = session.waveform
    changes = []
    
    for change in waveform.get_signal_values(var):
        t = change.time
        if start_time is not None and t < start_time:
            continue
        if end_time is not None and t > end_time:
            break
        
        changes.append({
            "time": t,
            "value": str(change.value)
        })
    
    if not changes:
        raise QueryError("NO_DATA", "No signal changes in specified time range")
    
    # Export based on format
    if format == "json":
        data = {
            "signal": signal_path,
            "changes": changes,
            "metadata": {
                "total_changes": len(changes),
                "time_range": {
                    "start": changes[0]["time"],
                    "end": changes[-1]["time"]
                }
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    elif format == "csv":
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Time", "Value"])
            for change in changes:
                writer.writerow([change["time"], change["value"]])
    
    else:
        raise QueryError("INVALID_FORMAT", f"Unsupported format: {format}")
    
    return {
        "output_file": output_path,
        "signal_path": signal_path,
        "format": format,
        "changes_exported": len(changes),
        "time_range": {
            "start": changes[0]["time"],
            "end": changes[-1]["time"]
        },
        "file_size": os.path.getsize(output_path)
    }
