PyWellen MCP - Waveform Analysis via Model Context Protocol
============================================================

PyWellen MCP is a powerful Model Context Protocol (MCP) server that enables LLM agents to interact with digital waveform files. It provides comprehensive tools for analyzing VCD, FST, GHW, and other waveform formats commonly used in hardware design and verification.

.. toctree::
   :maxdepth: 2
   :caption: Getting Started
   
   getting_started
   installation
   quick_reference

.. toctree::
   :maxdepth: 2
   :caption: User Guide
   
   core_operations
   signal_analysis
   hierarchy_navigation
   time_management
   comparison
   format_conversion

.. toctree::
   :maxdepth: 2
   :caption: Advanced Features
   
   llm_optimization
   export_integration
   performance
   best_practices

.. toctree::
   :maxdepth: 2
   :caption: Deployment
   
   deployment
   security
   troubleshooting

.. toctree::
   :maxdepth: 2
   :caption: Development
   
   api_reference
   architecture
   contributing
   changelog

Key Features
------------

**35+ MCP Tools** across 9 categories:

* **Core Operations**: Session and file management
* **Signal Analysis**: Read, search, and analyze signal values
* **Hierarchy Navigation**: Explore design hierarchy and signal structure
* **Time Management**: Time conversion and range operations
* **Comparison**: Signal and waveform comparison
* **Format Conversion**: Value formatting and type conversion
* **LLM Optimization**: Natural language query and signal summarization
* **Export/Integration**: CSV export, viewer integration, file monitoring
* **Advanced Features**: Performance optimization and error recovery

Why PyWellen MCP?
-----------------

**For Verification Engineers**:

* Analyze waveforms without leaving your LLM chat interface
* Natural language queries: "Show me all clock signals toggling at 100MHz"
* Automated signal correlation and debugging workflows
* Export data for further analysis or reporting

**For Hardware Designers**:

* Quick signal exploration and hierarchy navigation
* Compare signals across multiple waveforms
* Generate GTKWave save files programmatically
* Integrate with existing verification flows

**For Tool Developers**:

* Extensible MCP-based architecture
* Clean Python API for waveform analysis
* Support for multiple waveform formats
* Built-in caching and performance optimization

Quick Example
-------------

.. code-block:: json

   // Open a waveform file
   {
     "tool": "waveform_open",
     "arguments": {
       "file_path": "/path/to/design.vcd"
     }
   }
   
   // Search for clock signals
   {
     "tool": "signal_search",
     "arguments": {
       "session_id": "session-123",
       "pattern": "*clk*",
       "signal_type": "clock"
     }
   }
   
   // Get signal values in a time range
   {
     "tool": "signal_get_values",
     "arguments": {
       "session_id": "session-123",
       "signal_path": "top.clk",
       "start_time": "0",
       "end_time": "1000"
     }
   }

Supported Waveform Formats
---------------------------

* **VCD** (Value Change Dump) - IEEE 1364
* **FST** (Fast Signal Trace) - GTKWave optimized format
* **GHW** (GHDL Waveform) - VHDL simulation format
* **LXT/LXT2** - GTKWave compressed formats
* **VZT** - GTKWave compressed format

Requirements
------------

* Python 3.10 or later
* MCP client (e.g., Claude Desktop, VS Code with MCP extension)
* Optional: GTKWave, Verdi, or other waveform viewers

Installation
------------

.. code-block:: bash

   pip install pywellen-mcp

Or from source:

.. code-block:: bash

   git clone https://github.com/fvutils/pywellen-mcp.git
   cd pywellen-mcp
   pip install -e ".[dev]"

Quick Start
-----------

1. **Install the server**::

      pip install pywellen-mcp

2. **Configure your MCP client** (e.g., Claude Desktop):

   .. code-block:: json

      {
        "mcpServers": {
          "pywellen": {
            "command": "pywellen-mcp"
          }
        }
      }

3. **Start analyzing waveforms**:

   * Open a waveform file
   * Search for signals
   * Analyze signal values
   * Compare waveforms
   * Export results

Community and Support
---------------------

* **Documentation**: https://fvutils.github.io/pywellen-mcp
* **Source Code**: https://github.com/fvutils/pywellen-mcp
* **Issue Tracker**: https://github.com/fvutils/pywellen-mcp/issues
* **Discussions**: https://github.com/fvutils/pywellen-mcp/discussions

License
-------

Apache License 2.0 - See LICENSE file for details

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
