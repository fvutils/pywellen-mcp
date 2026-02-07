Export and Integration Tools
=============================

Overview
--------

The PyWellen MCP server includes tools for exporting waveform data and integrating with external tools and workflows. These tools enable:

* Exporting signal data to CSV and JSON formats
* Exporting design hierarchy to structured formats
* Loading and saving signal configuration files
* Launching external waveform viewers
* Monitoring files for changes
* Generating viewer-specific configuration files

These tools bridge the gap between PyWellen and external analysis tools, viewers, and workflows.

Export Tools
------------

export_to_csv
^^^^^^^^^^^^^

**Purpose**: Export signal data to CSV format for analysis in spreadsheets or data science tools.

**Parameters**:

* ``session_id`` (string, required): Active waveform session ID
* ``signal_paths`` (array, required): List of signal paths to export
* ``output_path`` (string, required): Path to output CSV file
* ``start_time`` (integer, optional): Start time for export range
* ``end_time`` (integer, optional): End time for export range
* ``include_header`` (boolean, optional): Include column headers (default: true)
* ``time_format`` (string, optional): "absolute" or "relative" (default: absolute)

**Returns**:

* ``output_file``: Path to created CSV file
* ``signals_exported``: Number of signals exported
* ``rows_written``: Number of data rows written
* ``time_range``: Actual time range exported
* ``format``: CSV format details

**Example Usage**::

    {
        "session_id": "abc123",
        "signal_paths": ["top.clk", "top.data", "top.valid"],
        "output_path": "/tmp/signals.csv",
        "time_format": "relative"
    }

**Output Format**::

    Time,top.clk,top.data,top.valid
    0,0,0x00,0
    5,0,0x00,1
    10,1,0xff,1
    15,1,0xff,0

**Use Cases**:

* Statistical analysis in R, Python (pandas), or Excel
* Plotting signal waveforms
* Correlation analysis between signals
* Export for regression testing

export_hierarchy_tree
^^^^^^^^^^^^^^^^^^^^^

**Purpose**: Export design hierarchy as structured tree for visualization or processing.

**Parameters**:

* ``session_id`` (string, required): Active session ID
* ``output_path`` (string, required): Path to output file
* ``format`` (string, optional): "json", "yaml", or "text" (default: json)
* ``include_variables`` (boolean, optional): Include variable details (default: true)
* ``include_metadata`` (boolean, optional): Include scope metadata (default: true)
* ``max_depth`` (integer, optional): Maximum tree depth (null = unlimited)

**Returns**:

* ``output_file``: Path to created file
* ``format``: Format used
* ``total_scopes``: Number of scopes exported
* ``total_variables``: Number of variables exported
* ``max_depth_reached``: Maximum depth in hierarchy

**Example - JSON Output**::

    {
        "design": "test.vcd",
        "scopes": [
            {
                "name": "top",
                "type": "Module",
                "metadata": {
                    "num_children": 2,
                    "num_variables": 3,
                    "depth": 0
                },
                "variables": [
                    {
                        "name": "clk",
                        "type": "Wire",
                        "direction": "Input",
                        "length": 1
                    }
                ],
                "children": [...]
            }
        ]
    }

**Example - Text Output**::

    Design: test.vcd
    
    ├─ top (Module)
      │  clk : Wire
      │  data : Reg
      ├─ cpu (Module)
        │  alu_out : Wire

**Use Cases**:

* Design visualization tools
* Documentation generation
* Hierarchy analysis
* Module extraction

export_signal_data
^^^^^^^^^^^^^^^^^^

**Purpose**: Export single signal's complete data to JSON or CSV.

**Parameters**:

* ``session_id`` (string, required): Active session ID
* ``signal_path`` (string, required): Signal to export
* ``output_path`` (string, required): Path to output file
* ``format`` (string, optional): "json" or "csv" (default: json)
* ``start_time`` (integer, optional): Start time for export range
* ``end_time`` (integer, optional): End time for export range

**Returns**:

* ``output_file``: Path to created file
* ``signal_path``: Signal that was exported
* ``format``: Format used
* ``changes_exported``: Number of changes written
* ``time_range``: Time range exported
* ``file_size``: Size of created file

**JSON Output Example**::

    {
        "signal": "top.clk",
        "changes": [
            {"time": 0, "value": "0"},
            {"time": 10, "value": "1"},
            {"time": 20, "value": "0"}
        ],
        "metadata": {
            "total_changes": 3,
            "time_range": {"start": 0, "end": 20}
        }
    }

Configuration Tools
-------------------

load_signal_list
^^^^^^^^^^^^^^^^

**Purpose**: Load signal lists and configurations from JSON/YAML files.

**Parameters**:

* ``session_id`` (string, required): Active session ID
* ``config_path`` (string, required): Path to configuration file

**Returns**:

* ``config_file``: Path to loaded file
* ``signals``: List of loaded signal paths
* ``groups``: Signal groups from config
* ``filters``: Filters from config
* ``metadata``: Configuration metadata
* ``validation``: Validation results (valid/invalid signals)

**Configuration File Format**::

    {
        "signals": [
            "top.clk",
            "top.data"
        ],
        "groups": {
            "control": ["top.valid", "top.ready", "top.enable"],
            "data": ["top.data", "top.addr"]
        },
        "filters": {
            "scope": "top.cpu",
            "types": ["Wire", "Reg"],
            "min_bitwidth": 8
        },
        "metadata": {
            "description": "Main control signals",
            "author": "user@example.com",
            "date": "2024-01-15"
        }
    }

**Use Cases**:

* Reusable signal selection for common debug scenarios
* Team-shared signal lists
* Workflow automation
* Regression test configurations

save_signal_list
^^^^^^^^^^^^^^^^

**Purpose**: Save signal lists to configuration files for reuse.

**Parameters**:

* ``session_id`` (string, required): Active session ID
* ``output_path`` (string, required): Path to output file
* ``signal_paths`` (array, required): Signals to save
* ``groups`` (object, optional): Signal groups
* ``filters`` (object, optional): Filter configuration
* ``metadata`` (object, optional): Metadata
* ``format`` (string, optional): "json" or "yaml" (default: json)

**Returns**:

* ``output_file``: Path to created file
* ``format``: Format used
* ``signals_saved``: Number of signals saved
* ``groups_saved``: Number of groups saved
* ``file_size``: Size of created file

Integration Tools
-----------------

integration_launch_viewer
^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: Launch external waveform viewer with waveform file.

**Supported Viewers**:

* **GTKWave**: Open-source waveform viewer
* **Verdi**: Synopsys Verdi
* **Simvision**: Cadence Simvision
* **DVE**: Synopsys DVE
* **Wave**: Generic wave viewer
* **Custom**: User-defined viewer command

**Parameters**:

* ``viewer`` (string, required): Viewer name or "custom"
* ``file_path`` (string, required): Path to waveform file
* ``save_file`` (string, optional): Optional save/config file
* ``additional_args`` (array, optional): Additional command arguments
* ``wait`` (boolean, optional): Wait for viewer to exit (default: false)

**Returns**:

* ``viewer``: Viewer launched
* ``command``: Full command executed
* ``pid``: Process ID (if not waiting)
* ``exit_code``: Exit code (if waiting)
* ``status``: "launched" or "completed"

**Example Usage**::

    {
        "viewer": "gtkwave",
        "file_path": "/path/to/waveform.vcd",
        "save_file": "/path/to/signals.gtkw"
    }

**Viewer-Specific Arguments**:

* **GTKWave**: Save file loaded with ``-a`` flag
* **Simvision**: Save file loaded with ``-input`` flag
* **Verdi**: Save file loaded with ``-sswr`` flag

**Custom Viewer Example**::

    {
        "viewer": "custom",
        "file_path": "/path/to/wave.vcd",
        "additional_args": ["my_viewer", "--fullscreen", "{file}"]
    }

integration_watch_file
^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: Monitor waveform file for changes (useful for live simulation).

**Parameters**:

* ``file_path`` (string, required): Path to file to monitor
* ``interval`` (integer, optional): Check interval in seconds (default: 5)
* ``max_checks`` (integer, optional): Maximum checks (default: 60)

**Returns**:

* ``file_path``: File being monitored
* ``status``: "unchanged", "modified", "created", "deleted", or "not_found"
* ``last_modified``: Last modification timestamp
* ``file_size``: Current file size
* ``size_change``: Size difference (if modified)
* ``checks_performed``: Number of checks performed

**Example Usage**::

    {
        "file_path": "/sim/output/waves.vcd",
        "interval": 5,
        "max_checks": 120
    }

**Use Cases**:

* Live simulation monitoring
* Auto-reload workflows
* Simulation completion detection
* File update notifications

integration_generate_gtkwave_save
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: Generate GTKWave save file (.gtkw) for quick signal viewing.

**Parameters**:

* ``session_id`` (string, required): Active session ID
* ``output_path`` (string, required): Path to .gtkw file
* ``signal_paths`` (array, required): Signals to include
* ``time_range`` (object, optional): Time range dict with start/end
* ``group_signals`` (boolean, optional): Group by hierarchy (default: true)

**Returns**:

* ``output_file``: Path to created save file
* ``format``: "gtkwave_save"
* ``signals_included``: Number of signals included
* ``groups_created``: Number of signal groups
* ``file_size``: Size of created file

**Generated Save File**::

    [*]
    [*] GTKWave Save File
    [*] Generated by PyWellen MCP
    [*]
    
    [dumpfile] "(null)"
    [timestart] 0
    [timeend] 1000
    
    @top.cpu
    top.cpu.clk
    top.cpu.data
    top.cpu.valid
    @-
    
    @top.mem
    top.mem.addr
    top.mem.data
    @-

**Use Cases**:

* Pre-configured waveform views
* Team-shared debug setups
* Automated test result viewing
* Quick signal inspection

Common Workflows
----------------

Workflow 1: Export for Analysis
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Export signals to CSV for analysis in Python/R/Excel::

    1. Open waveform with waveform_open
    2. Find signals of interest with hierarchy_search
    3. Export to CSV with export_to_csv
    4. Analyze in external tool (pandas, Excel, etc.)

Workflow 2: Save and Share Signal Lists
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create reusable signal configurations::

    1. Open waveform and explore hierarchy
    2. Identify important signals
    3. Save to config with save_signal_list
    4. Share config file with team
    5. Load with load_signal_list in future sessions

Workflow 3: Launch Viewer with Pre-configured Signals
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Quick waveform viewing with pre-loaded signals::

    1. Open waveform session
    2. Generate GTKWave save with integration_generate_gtkwave_save
    3. Launch viewer with integration_launch_viewer
    4. Signals are pre-loaded and grouped

Workflow 4: Live Simulation Monitoring
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Monitor ongoing simulation::

    1. Start simulation (generates waveform file)
    2. Use integration_watch_file to monitor for updates
    3. When modified, open new session with waveform_open
    4. Analyze latest data
    5. Repeat until simulation completes

Best Practices
--------------

File Paths
^^^^^^^^^^

* Always use absolute paths for reliability
* Check directory permissions before export
* Use temporary directories for throwaway exports
* Organize exports by date/session for tracking

Configuration Files
^^^^^^^^^^^^^^^^^^^

* Use JSON for simple configs
* Use YAML for complex, human-editable configs
* Include metadata (author, date, description)
* Version control configuration files
* Document signal groupings and filters

External Tool Integration
^^^^^^^^^^^^^^^^^^^^^^^^^^

* Check viewer availability before launching
* Use save files for consistent viewer configuration
* Launch viewers in background (wait=false) for responsiveness
* Provide additional_args for custom options

Performance
^^^^^^^^^^^

* Limit time ranges for large exports
* Use signal_summarize before full export
* Export only needed signals
* Consider batch operations for multiple exports

File Format Recommendations
----------------------------

CSV Export
^^^^^^^^^^

**Pros**:
* Universal compatibility
* Easy to parse
* Works with spreadsheets

**Cons**:
* Large file sizes
* No hierarchy information
* Text-based (slower for large data)

**Best For**:
* Spreadsheet analysis
* Statistical processing
* Quick data inspection

JSON Export
^^^^^^^^^^^

**Pros**:
* Structured format
* Supports metadata
* Easy to parse programmatically

**Cons**:
* Larger than binary formats
* Slower for huge datasets

**Best For**:
* Tool integration
* Configuration files
* Hierarchical data

YAML Export
^^^^^^^^^^^

**Pros**:
* Human-readable
* Supports comments
* Good for configuration

**Cons**:
* Requires pyyaml package
* Slower parsing than JSON

**Best For**:
* Configuration files
* Human-edited files
* Documentation

Limitations
-----------

* File watching is polling-based (not event-driven)
* Large CSV exports may consume significant memory
* Viewer integration requires viewer to be installed
* YAML support requires optional pyyaml package
* Custom viewer commands are platform-dependent

See Also
--------

* :doc:`signal_analysis` - For analyzing signals before export
* :doc:`debugging_tools` - For finding signals to export
* :doc:`llm_optimization` - For context-efficient data access
* :doc:`api_reference` - Complete API documentation
