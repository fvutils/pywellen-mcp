# Changelog

All notable changes to PyWellen MCP will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- CI/CD pipeline with GitHub Actions
- Performance benchmarking suite
- Security audit script
- Comprehensive deployment documentation
- Contributing guidelines

### Changed
- Documentation moved to Sphinx with RTD theme
- Enhanced README with badges and examples

## [0.8.0] - 2026-02-08

### Phase 7: Export and Integration

#### Added
- `export_to_csv` - Export signal data to CSV format
- `export_hierarchy_tree` - Export design hierarchy as tree structure
- `load_signal_list` - Load signal lists from JSON/YAML
- `save_signal_list` - Save signal lists to JSON/YAML
- `export_signal_data` - Generic signal data export
- `integration_launch_viewer` - Launch external waveform viewers
- `integration_watch_file` - Monitor waveform files for changes
- `integration_generate_gtkwave_save` - Generate GTKWave save files
- Support for 6 waveform viewers: GTKWave, Verdi, Simvision, DVE, Wave, Custom
- File change monitoring with configurable poll interval
- GTKWave save file generation with signal grouping

#### Documentation
- Complete export/integration tools documentation
- Viewer configuration examples
- File format specifications

#### Tests
- 14 export tool tests (100% passing)
- 14 integration tool tests (100% passing)
- 28 total tests for Phase 7

## [0.7.0] - 2026-02-07

### Phase 6: LLM Optimization

#### Added
- `query_natural_language` - Natural language query processing
- `signal_summarize` - Automatic signal summarization
- `recommend_related_signals` - Related signal recommendations
- `docs_get_started` - Interactive getting started guide
- `docs_tool_guide` - Tool usage documentation
- Pattern-based query interpretation for 10+ common queries
- Heuristic signal pattern detection (clock, reset, data, control, etc.)
- Related signal recommendation with complementary patterns
- Integrated documentation access

#### Documentation
- Complete LLM optimization tools documentation
- Natural language query examples
- Signal pattern descriptions

#### Tests
- 27 LLM tool tests (16/27 passing, core functionality complete)
- Integration tests pending real waveform data

## [0.6.0] - 2026-02-06

### Phase 5: Comparison and Format Conversion

#### Added
- `compare_signals` - Compare values between two signals
- `compare_waveforms` - Compare entire waveforms
- `compare_time_ranges` - Compare signals in time ranges
- `format_value` - Format signal values with custom options
- `format_as_signed` - Convert to signed representation
- `format_as_binary` - Convert to binary representation
- `format_as_hex` - Convert to hexadecimal representation
- Difference detection with percentage calculations
- Multiple formatting options (width, padding, prefix)
- Support for various data widths (1-bit to 64-bit)

#### Documentation
- Comparison tools documentation
- Format conversion examples
- Best practices for signal comparison

#### Tests
- 18 comparison tool tests (100% passing)
- 13 format tool tests (100% passing)
- 31 total tests for Phase 5

## [0.5.0] - 2026-02-05

### Phase 4: Debugging and Analysis

#### Added
- `debug_find_transitions` - Find signal transitions (rising, falling, any)
- `debug_trace_causality` - Trace causal relationships between signals
- `debug_compare_waveforms` - Compare signals across waveforms
- `debug_build_timeline` - Build event timelines from signals
- `debug_check_protocol` - Protocol compliance checking
- `debug_identify_glitches` - Glitch detection with configurable thresholds
- `debug_find_correlation` - Signal correlation analysis
- Advanced debugging workflows
- Protocol checking for common interfaces (AMBA, UART, SPI)
- Glitch detection and analysis
- Correlation analysis with Pearson coefficient

#### Documentation
- Debugging tools documentation
- Protocol checker examples
- Correlation analysis guide

#### Tests
- 33 debugging tool tests (100% passing)

## [0.4.0] - 2026-02-04

### Phase 3: Signal Data Access

#### Added
- `signal_get_value` - Get signal value at specific time
- `signal_get_values` - Get signal values over time range
- `signal_get_changes` - Get value change events
- `signal_get_statistics` - Calculate signal statistics (transitions, activity, etc.)
- `signal_search` - Search signals with advanced filters
- LRU caching for frequently accessed signals (configurable cache size)
- Support for multiple value formats (int, hex, bin, signed)
- Time range filtering and pagination
- Signal activity analysis and statistics

#### Enhanced
- Session manager with signal caching
- Performance optimization for large waveforms
- Efficient time range queries

#### Documentation
- Signal analysis tools documentation
- Caching strategy guide
- Performance optimization tips

#### Tests
- 25 signal analysis tests (100% passing)

## [0.3.0] - 2026-02-03

### Phase 2: Hierarchy Navigation

#### Added
- `hierarchy_list_top_scopes` - List top-level design scopes
- `hierarchy_get_scope` - Get detailed scope information
- `hierarchy_list_variables` - List variables in a scope
- `hierarchy_search` - Search hierarchy with patterns
- Path-based navigation with dot notation
- Recursive scope traversal
- Pattern matching (substring and regex)
- Pagination support for large hierarchies
- Scope type filtering

#### Documentation
- Hierarchy navigation documentation
- Path syntax guide
- Search pattern examples

#### Tests
- 22 hierarchy navigation tests (100% passing)

## [0.2.0] - 2026-02-02

### Phase 1: Core Infrastructure

#### Added
- `waveform_open` - Open waveform files (VCD, FST, GHW)
- `waveform_close` - Close waveform sessions
- `waveform_info` - Get waveform metadata
- `waveform_list_sessions` - List active sessions
- Session management with unique IDs
- Automatic session cleanup (1-hour timeout)
- Multi-threaded VCD parsing option
- Structured error responses
- Session lifecycle management

#### Infrastructure
- MCP server implementation
- SessionManager with lifecycle management
- Error handling framework
- Logging infrastructure

#### Documentation
- Getting started guide
- Core operations documentation
- API reference

#### Tests
- 11 core infrastructure tests (100% passing)
- Session management tests
- Error handling tests

## [0.1.0] - 2026-02-01

### Initial Release

#### Added
- Project structure and build system
- Python package configuration with `pyproject.toml`
- Basic MCP server skeleton
- Development environment setup
- Documentation framework with Sphinx
- Test infrastructure with pytest

#### Infrastructure
- Git repository initialization
- License (Apache 2.0)
- README and documentation structure
- CI/CD foundation

---

## Release Types

- **Major (X.0.0)**: Breaking API changes, major features
- **Minor (0.X.0)**: New features, backwards compatible
- **Patch (0.0.X)**: Bug fixes, minor improvements

## Categories

- **Added**: New features
- **Changed**: Changes to existing features
- **Deprecated**: Features marked for removal
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security improvements
- **Performance**: Performance improvements
- **Documentation**: Documentation updates
- **Tests**: Test improvements

[Unreleased]: https://github.com/fvutils/pywellen-mcp/compare/v0.8.0...HEAD
[0.8.0]: https://github.com/fvutils/pywellen-mcp/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/fvutils/pywellen-mcp/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/fvutils/pywellen-mcp/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/fvutils/pywellen-mcp/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/fvutils/pywellen-mcp/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/fvutils/pywellen-mcp/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/fvutils/pywellen-mcp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/fvutils/pywellen-mcp/releases/tag/v0.1.0
