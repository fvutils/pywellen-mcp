# PyWellen MCP - Waveform Analysis via Model Context Protocol

[![Tests](https://github.com/fvutils/pywellen-mcp/workflows/CI/badge.svg)](https://github.com/fvutils/pywellen-mcp/actions)
[![Documentation](https://img.shields.io/badge/docs-latest-blue.svg)](https://fvutils.github.io/pywellen-mcp)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

PyWellen MCP is a powerful [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that enables LLM agents to interact with digital waveform files. Analyze VCD, FST, GHW, and other waveform formats using natural language queries and AI-powered tools.

## ✨ Features

- **🎯 35+ MCP Tools** across 9 comprehensive categories
- **📊 Multi-format Support**: VCD, FST, GHW, LXT, LXT2, VZT waveforms
- **🔍 Natural Language Queries**: Ask about signals using plain English
- **⚡ High Performance**: Multi-threaded parsing, LRU caching, optimized algorithms
- **🔗 External Integrations**: GTKWave, Verdi, Simvision viewer support
- **📤 Export Capabilities**: CSV, JSON, YAML, hierarchy trees, signal lists
- **🧠 LLM Optimization**: Signal summarization, pattern detection, recommendation
- **🔒 Production Ready**: Comprehensive error handling, security, monitoring

## 🚀 Quick Start

### Installation

```bash
# From PyPI (when published)
pip install pywellen-mcp

# From source
git clone https://github.com/fvutils/pywellen-mcp.git
cd pywellen-mcp
pip install -e ".[dev]"
```

### Configuration

Add to your MCP client configuration (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "pywellen": {
      "command": "pywellen-mcp",
      "args": []
    }
  }
}
```

### Example Usage

```python
# Chat with your LLM using natural language:
"Open the waveform file /path/to/design.vcd"
"Show me all clock signals"
"What's the value of top.cpu.reset at time 1000?"
"Compare signals clk_a and clk_b"
"Export the signal data to CSV"
```

## 📊 Current Status

**35 Tools Implemented** | **182/193 Tests Passing** | **94.3% Success Rate**

- ✅ **Phase 1**: Core Infrastructure (4 tools)
- ✅ **Phase 2**: Hierarchy Navigation (4 tools)
- ✅ **Phase 3**: Signal Data Access (5 tools)
- ✅ **Phase 4**: Debugging & Analysis (7 tools)
- ✅ **Phase 5**: Comparison & Format Conversion (7 tools)
- ✅ **Phase 6**: LLM Optimization (5 tools)
- ✅ **Phase 7**: Export & Integration (8 tools)
- 🚧 **Phase 8**: Production Readiness (CI/CD, security, monitoring)

## 🛠️ Tool Categories

### Core Operations (4 tools)
- `waveform_open` - Open waveform files (VCD, FST, GHW)
- `waveform_close` - Close sessions
- `waveform_info` - Get waveform metadata
- `waveform_list_sessions` - List active sessions

### Hierarchy Navigation (4 tools)
- `hierarchy_list_top_scopes` - List top-level design scopes
- `hierarchy_get_scope` - Get scope details
- `hierarchy_list_variables` - List variables in a scope
- `hierarchy_search` - Search hierarchy with patterns

### Signal Analysis (5 tools)
- `signal_get_value` - Get signal value at specific time
- `signal_get_values` - Get values over time range
- `signal_get_changes` - Get value change events
- `signal_get_statistics` - Calculate signal statistics
- `signal_search` - Search signals with filters

### Time Management (2 tools)
- `time_get_range` - Get simulation time range
- `time_convert` - Convert time units

### Debugging & Analysis (7 tools)
- `debug_find_transitions` - Find signal transitions
- `debug_trace_causality` - Trace signal causality
- `debug_compare_waveforms` - Compare waveforms
- `debug_build_timeline` - Build event timelines
- `debug_check_protocol` - Protocol checker
- `debug_identify_glitches` - Glitch detection
- `debug_find_correlation` - Signal correlation

### Comparison (3 tools)
- `compare_signals` - Compare signal values
- `compare_waveforms` - Compare entire waveforms
- `compare_time_ranges` - Compare time ranges

### Format Conversion (4 tools)
- `format_value` - Format signal values
- `format_as_signed` - Convert to signed values
- `format_as_binary` - Binary representation
- `format_as_hex` - Hex representation

### LLM Optimization (5 tools)
- `query_natural_language` - Natural language queries
- `signal_summarize` - Automatic signal summarization
- `recommend_related_signals` - Signal recommendations
- `docs_get_started` - Getting started guide
- `docs_tool_guide` - Tool usage documentation

### Export & Integration (8 tools)
- `export_to_csv` - Export signals to CSV
- `export_hierarchy_tree` - Export design hierarchy
- `load_signal_list` - Load signal configurations
- `save_signal_list` - Save signal configurations
- `export_signal_data` - Export to JSON/YAML
- `integration_launch_viewer` - Launch external viewers
- `integration_watch_file` - File change monitoring
- `integration_generate_gtkwave_save` - Generate GTKWave saves

## 📖 Documentation

- **[Getting Started](docs/getting_started.rst)** - Installation and first steps
- **[Quick Reference](docs/quick_reference.rst)** - Common workflows
- **[API Reference](docs/api_reference.rst)** - Complete tool documentation
- **[Best Practices](docs/best_practices.rst)** - Performance and optimization
- **[Deployment Guide](docs/deployment.rst)** - Production deployment
- **[Full Documentation](https://fvutils.github.io/pywellen-mcp)** - Complete docs

## 🎯 Use Cases

### For Verification Engineers
- Analyze waveforms without leaving your LLM chat
- Natural language debugging: "Show me when reset goes low"
- Automated signal correlation workflows
- Quick protocol compliance checks

### For Hardware Designers
- Interactive design exploration
- Compare pre/post synthesis waveforms
- Generate test reports automatically
- Integration with existing EDA tools

### For Tool Developers
- MCP-based waveform analysis API
- Extensible plugin architecture
- Support for custom waveform formats
- Python-based scripting interface

## 🔧 Advanced Features

### Performance Optimization
- **Multi-threaded VCD parsing** for faster file loading
- **LRU caching** for frequently accessed signals
- **Lazy loading** of signal data on demand
- **Efficient time range queries** with binary search

### Security
- **Path validation** prevents directory traversal
- **Command injection protection** for viewer launches
- **File permission checks** before operations
- **Session isolation** prevents cross-session access

### Error Handling
- **Structured error responses** with context
- **Recovery strategies** for common failures
- **Graceful degradation** on missing data
- **Detailed logging** for debugging

## 🧪 Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=pywellen_mcp --cov-report=html

# Run specific category
pytest tests/unit/test_tools_llm.py
pytest tests/unit/test_tools_export.py
```

### Performance Benchmarking

```bash
# Run benchmark suite
python scripts/benchmark.py

# Profile specific operations
python -m cProfile -s cumtime scripts/benchmark.py
```

### Security Audit

```bash
# Run security checks
python scripts/security_audit.py

# Check specific categories
python scripts/security_audit.py --check-paths
python scripts/security_audit.py --check-commands
```

## 🏗️ Architecture

### Components

```
pywellen-mcp/
├── src/pywellen_mcp/
│   ├── server.py              # MCP server implementation
│   ├── session.py             # Session management
│   ├── tools_waveform.py      # Core waveform operations
│   ├── tools_hierarchy.py     # Hierarchy navigation
│   ├── tools_signal.py        # Signal analysis
│   ├── tools_time.py          # Time management
│   ├── tools_debug.py         # Debugging tools
│   ├── tools_compare.py       # Comparison operations
│   ├── tools_format.py        # Format conversion
│   ├── tools_llm.py           # LLM optimization
│   ├── tools_export.py        # Export capabilities
│   └── tools_integration.py   # External integrations
├── tests/
│   └── unit/                  # Comprehensive unit tests
├── scripts/
│   ├── benchmark.py           # Performance benchmarks
│   └── security_audit.py      # Security checks
└── docs/                      # Sphinx documentation
```

### Session Lifecycle

1. **Open**: `waveform_open` creates session with unique ID
2. **Use**: Tools access session via session_id parameter
3. **Cleanup**: Automatic after 1 hour timeout or explicit close

### Error Handling

All operations return structured errors:
```json
{
  "error": "SESSION_NOT_FOUND",
  "message": "Session abc123 not found",
  "context": {
    "session_id": "abc123",
    "active_sessions": ["def456"]
  }
}
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](docs/contributing.rst).

### Development Setup

```bash
# Clone repository
git clone https://github.com/fvutils/pywellen-mcp.git
cd pywellen-mcp

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest
```

### Code Standards

- **Style**: Black formatting, PEP 8 compliance
- **Type Hints**: Full type annotations
- **Documentation**: Docstrings for all public APIs
- **Testing**: Minimum 80% code coverage

## 📝 Roadmap

### Phase 8: Production Readiness (In Progress)
- [x] CI/CD pipeline (GitHub Actions)
- [x] Performance benchmarking suite
- [x] Security audit script
- [x] Comprehensive documentation
- [ ] Memory profiling
- [ ] Integration tests with real waveforms
- [ ] Version 1.0.0 release

### Future Enhancements
- [ ] WebSocket-based streaming for large waveforms
- [ ] Distributed analysis for massive designs
- [ ] Machine learning-based anomaly detection
- [ ] Plugin system for custom analyzers
- [ ] Support for SystemVerilog assertions
- [ ] Real-time waveform monitoring

## 🙏 Acknowledgments

- **[Wellen](https://github.com/ekiwi/wellen)** - Rust waveform parsing library
- **[MCP](https://modelcontextprotocol.io/)** - Model Context Protocol specification
- **[Anthropic](https://www.anthropic.com/)** - MCP development and Claude integration
- **GTKWave, Verdi, Simvision** - Waveform viewer integrations

## 📄 License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.

## 🔗 Links

- **Homepage**: https://github.com/fvutils/pywellen-mcp
- **Documentation**: https://fvutils.github.io/pywellen-mcp
- **PyPI**: https://pypi.org/project/pywellen-mcp/
- **Issues**: https://github.com/fvutils/pywellen-mcp/issues
- **Discussions**: https://github.com/fvutils/pywellen-mcp/discussions

## 📧 Contact

- **Author**: Matthew Ballance
- **Email**: mballance@fvutils.com
- **GitHub**: [@mballance](https://github.com/mballance)

---

**Made with ❤️ by the FVUtils community**

