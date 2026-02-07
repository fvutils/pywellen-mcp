"""
Integration tools for external tool interaction and file monitoring.

This module provides tools for integrating with external waveform viewers
and monitoring waveform files for changes.
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from .session import SessionManager
from .errors import FileError, ResourceError


# Common waveform viewer commands
VIEWER_COMMANDS = {
    "gtkwave": ["gtkwave", "{file}"],
    "simvision": ["simvision", "{file}"],
    "verdi": ["verdi", "-ssf", "{file}"],
    "dve": ["dve", "-vpd", "{file}"],
    "wave": ["wave", "{file}"]
}


async def integration_launch_viewer(
    viewer: str,
    file_path: str,
    save_file: Optional[str] = None,
    additional_args: Optional[List[str]] = None,
    wait: Optional[bool] = False
) -> Dict[str, Any]:
    """
    Launch external waveform viewer with the specified file.
    
    Supports common waveform viewers like GTKWave, Verdi, Simvision, etc.
    Can optionally load a save file with signal selections and settings.
    
    Args:
        viewer: Viewer name ("gtkwave", "simvision", "verdi", "dve", "wave", "custom")
        file_path: Path to waveform file
        save_file: Optional save/configuration file for viewer
        additional_args: Additional command line arguments
        wait: Wait for viewer to exit (default: false)
        
    Returns:
        Dictionary containing:
        - viewer: Viewer launched
        - command: Command executed
        - pid: Process ID (if not waiting)
        - exit_code: Exit code (if waiting)
        - status: Launch status
        
    Example:
        integration_launch_viewer(
            viewer="gtkwave",
            file_path="/path/to/waveform.vcd",
            save_file="/path/to/signals.gtkw"
        )
    """
    # Validate waveform file exists
    if not os.path.exists(file_path):
        raise FileError("FILE_NOT_FOUND", f"Waveform file not found: {file_path}")
    
    if not os.access(file_path, os.R_OK):
        raise FileError("PERMISSION_DENIED", f"Cannot read file: {file_path}")
    
    # Validate save file if provided
    if save_file:
        if not os.path.exists(save_file):
            raise FileError("FILE_NOT_FOUND", f"Save file not found: {save_file}")
        
        if not os.access(save_file, os.R_OK):
            raise FileError("PERMISSION_DENIED", f"Cannot read save file: {save_file}")
    
    # Build command
    if viewer in VIEWER_COMMANDS:
        command = [arg.format(file=file_path) for arg in VIEWER_COMMANDS[viewer]]
        
        # Add save file for supported viewers
        if save_file:
            if viewer == "gtkwave":
                command.extend(["-a", save_file])
            elif viewer == "simvision":
                command.extend(["-input", save_file])
            elif viewer == "verdi":
                command.extend(["-sswr", save_file])
    
    elif viewer == "custom":
        # Custom viewer command - use additional_args as full command
        if not additional_args:
            raise ResourceError("INVALID_ARGS", "Custom viewer requires additional_args with full command")
        command = [arg.format(file=file_path) for arg in additional_args]
    
    else:
        raise ResourceError("UNKNOWN_VIEWER", f"Unsupported viewer: {viewer}")
    
    # Add additional arguments
    if additional_args and viewer != "custom":
        command.extend(additional_args)
    
    # Check if viewer executable exists
    viewer_exe = command[0]
    if not _command_exists(viewer_exe):
        raise FileError("EXECUTABLE_NOT_FOUND", f"Viewer executable not found: {viewer_exe}")
    
    try:
        # Launch viewer
        if wait:
            result = subprocess.run(command, capture_output=True, text=True)
            return {
                "viewer": viewer,
                "command": " ".join(command),
                "exit_code": result.returncode,
                "status": "completed",
                "stdout": result.stdout[:1000] if result.stdout else None,  # Truncate
                "stderr": result.stderr[:1000] if result.stderr else None
            }
        else:
            process = subprocess.Popen(command)
            return {
                "viewer": viewer,
                "command": " ".join(command),
                "pid": process.pid,
                "status": "launched",
                "note": "Viewer launched in background. Use PID to track process."
            }
    
    except PermissionError as e:
        raise FileError("PERMISSION_DENIED", f"Permission denied launching viewer: {e}")
    except Exception as e:
        raise ResourceError("LAUNCH_FAILED", f"Failed to launch viewer: {e}")


async def integration_watch_file(
    file_path: str,
    interval: Optional[int] = 5,
    max_checks: Optional[int] = 60
) -> Dict[str, Any]:
    """
    Monitor waveform file for changes.
    
    Watches a file for modifications, useful for live simulation monitoring.
    Note: This is a synchronous check; for continuous monitoring, call repeatedly.
    
    Args:
        file_path: Path to waveform file to monitor
        interval: Check interval in seconds (default: 5)
        max_checks: Maximum number of checks before returning (default: 60)
        
    Returns:
        Dictionary containing:
        - file_path: File being monitored
        - status: "unchanged", "modified", "created", "deleted"
        - last_modified: Last modification timestamp
        - file_size: Current file size
        - checks_performed: Number of checks performed
        
    Example:
        integration_watch_file(
            file_path="/path/to/waveform.vcd",
            interval=5,
            max_checks=10
        )
    """
    # Validate path
    if not os.path.exists(file_path):
        return {
            "file_path": file_path,
            "status": "not_found",
            "exists": False,
            "note": "File does not exist yet. May be created by simulation."
        }
    
    # Get initial file info
    try:
        initial_stat = os.stat(file_path)
        initial_mtime = initial_stat.st_mtime
        initial_size = initial_stat.st_size
    except Exception as e:
        raise FileError("STAT_FAILED", f"Cannot stat file: {e}")
    
    # Monitor for changes
    checks_performed = 0
    status = "unchanged"
    
    for _ in range(max_checks):
        time.sleep(interval)
        checks_performed += 1
        
        # Check if file still exists
        if not os.path.exists(file_path):
            status = "deleted"
            return {
                "file_path": file_path,
                "status": status,
                "checks_performed": checks_performed,
                "note": "File was deleted during monitoring"
            }
        
        # Check for modifications
        try:
            current_stat = os.stat(file_path)
            current_mtime = current_stat.st_mtime
            current_size = current_stat.st_size
            
            if current_mtime > initial_mtime or current_size != initial_size:
                status = "modified"
                return {
                    "file_path": file_path,
                    "status": status,
                    "last_modified": current_mtime,
                    "file_size": current_size,
                    "size_change": current_size - initial_size,
                    "checks_performed": checks_performed,
                    "note": "File was modified during monitoring"
                }
        
        except Exception as e:
            raise FileError("MONITOR_FAILED", f"Failed to monitor file: {e}")
    
    # Max checks reached without changes
    return {
        "file_path": file_path,
        "status": status,
        "last_modified": initial_mtime,
        "file_size": initial_size,
        "checks_performed": checks_performed,
        "note": f"No changes detected after {max_checks} checks"
    }


async def integration_generate_gtkwave_save(
    session_manager: SessionManager,
    session_id: str,
    output_path: str,
    signal_paths: List[str],
    time_range: Optional[Dict[str, int]] = None,
    group_signals: Optional[bool] = True
) -> Dict[str, Any]:
    """
    Generate GTKWave save file (.gtkw) for signal viewing.
    
    Creates a GTKWave save file that pre-loads specified signals,
    making it easy to open waveforms with pre-configured views.
    
    Args:
        session_id: Active waveform session ID
        output_path: Path to output .gtkw file
        signal_paths: List of signals to include
        time_range: Optional time range dict with 'start' and 'end'
        group_signals: Group signals by hierarchy (default: true)
        
    Returns:
        Dictionary containing:
        - output_file: Path to created save file
        - signals_included: Number of signals included
        - groups_created: Number of signal groups
        
    Example:
        integration_generate_gtkwave_save(
            session_id="abc123",
            output_path="/tmp/signals.gtkw",
            signal_paths=["top.clk", "top.data", "top.valid"]
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
    
    # Validate signals
    valid_signals = []
    for signal_path in signal_paths:
        var = hierarchy.get_var_by_name(signal_path)
        if var:
            valid_signals.append(signal_path)
    
    if not valid_signals:
        raise ResourceError("NO_VALID_SIGNALS", "No valid signals provided")
    
    # Group signals by hierarchy if requested
    groups = {}
    if group_signals:
        for signal_path in valid_signals:
            parts = signal_path.split('.')
            if len(parts) > 1:
                group_name = '.'.join(parts[:-1])
                if group_name not in groups:
                    groups[group_name] = []
                groups[group_name].append(signal_path)
            else:
                if "top" not in groups:
                    groups["top"] = []
                groups["top"].append(signal_path)
    else:
        groups["signals"] = valid_signals
    
    # Write GTKWave save file
    with open(output_path, 'w') as f:
        # Header
        f.write("[*]\n")
        f.write("[*] GTKWave Save File\n")
        f.write("[*] Generated by PyWellen MCP\n")
        f.write("[*]\n\n")
        
        # Dumpfile (placeholder - will be overridden when loaded)
        f.write("[dumpfile] \"(null)\"\n")
        
        # Time range if specified
        if time_range:
            f.write(f"[timestart] {time_range.get('start', 0)}\n")
            if 'end' in time_range:
                f.write(f"[timeend] {time_range['end']}\n")
        
        f.write("\n")
        
        # Signals grouped
        for group_name, group_signals in groups.items():
            if len(groups) > 1:
                f.write(f"@{group_name}\n")
            
            for signal in group_signals:
                f.write(f"{signal}\n")
            
            if len(groups) > 1:
                f.write("@-\n\n")
    
    return {
        "output_file": output_path,
        "format": "gtkwave_save",
        "signals_included": len(valid_signals),
        "groups_created": len(groups),
        "file_size": os.path.getsize(output_path)
    }


def _command_exists(command: str) -> bool:
    """Check if a command exists in PATH."""
    from shutil import which
    return which(command) is not None
