Deployment Guide
================

This guide covers deploying PyWellen MCP Server to production environments.

Prerequisites
-------------

System Requirements
^^^^^^^^^^^^^^^^^^^

* **Python**: 3.10 or later
* **Operating System**: Linux, macOS, or Windows
* **Memory**: Minimum 512MB RAM, recommended 2GB+ for large waveforms
* **Disk Space**: 100MB for installation, additional space for waveform files

Dependencies
^^^^^^^^^^^^

Core dependencies (automatically installed):

* ``mcp`` - MCP protocol implementation
* ``pydantic`` - Data validation and settings management

Optional dependencies:

* ``pyyaml`` - YAML configuration file support
* ``wellen`` - Waveform file parsing (when using real waveforms)

Installation
------------

From PyPI
^^^^^^^^^

Once published, install via pip::

    pip install pywellen-mcp

From Source
^^^^^^^^^^^

For development or latest features::

    git clone https://github.com/fvutils/pywellen-mcp.git
    cd pywellen-mcp
    pip install -e ".[dev]"

Using IVPM
^^^^^^^^^^

For integrated project environments::

    # Add to ivpm.yaml
    packages:
      - pywellen-mcp

    # Update packages
    ivpm update

Configuration
-------------

Environment Variables
^^^^^^^^^^^^^^^^^^^^^

* ``PYWELLEN_MAX_SESSIONS`` - Maximum concurrent sessions (default: 10)
* ``PYWELLEN_SESSION_TIMEOUT`` - Session timeout in seconds (default: 3600)
* ``PYWELLEN_LOG_LEVEL`` - Logging level (default: INFO)

Configuration File
^^^^^^^^^^^^^^^^^^

Create ``config.json`` in your project directory::

    {
      "max_sessions": 10,
      "session_timeout": 3600,
      "signal_cache_size": 100,
      "log_level": "INFO",
      "enable_file_validation": true
    }

Running the Server
------------------

Standalone Mode
^^^^^^^^^^^^^^^

Run the MCP server directly::

    pywellen-mcp

The server listens on stdin/stdout for MCP protocol messages.

With MCP Client
^^^^^^^^^^^^^^^

Configure in your MCP client (e.g., Claude Desktop)::

    {
      "mcpServers": {
        "pywellen": {
          "command": "pywellen-mcp",
          "args": []
        }
      }
    }

Docker Deployment
^^^^^^^^^^^^^^^^^

Create a Dockerfile::

    FROM python:3.11-slim
    
    WORKDIR /app
    
    # Install dependencies
    COPY pyproject.toml .
    RUN pip install .
    
    # Copy application
    COPY src/ src/
    
    # Run server
    CMD ["pywellen-mcp"]

Build and run::

    docker build -t pywellen-mcp .
    docker run -i pywellen-mcp

Production Considerations
-------------------------

Performance Tuning
^^^^^^^^^^^^^^^^^^

**Session Management**:

* Adjust ``max_sessions`` based on available memory
* Rule of thumb: 200MB RAM per active session
* Monitor session count and cleanup expired sessions

**Signal Caching**:

* Increase ``signal_cache_size`` for frequently accessed signals
* Cache size of 100-500 typical for production
* Monitor cache hit rates

**File Handling**:

* Use local storage for waveform files (not network mounts)
* Implement file rotation for temporary exports
* Set up disk space monitoring

Memory Management
^^^^^^^^^^^^^^^^^

**Large Waveform Files**:

* Files >1GB may require significant memory
* Consider splitting large analyses into chunks
* Use time range filtering to limit data loaded

**Session Cleanup**:

* Automatic cleanup runs every hour
* Manually trigger with session management tools
* Monitor memory usage and adjust timeouts

**Export Operations**:

* CSV exports load all time points in memory
* Use time range filtering for large exports
* Consider streaming exports for huge datasets

Security
--------

File Access Control
^^^^^^^^^^^^^^^^^^^

**Path Validation**:

* All file paths are validated and resolved to absolute paths
* Directory existence and write permissions checked before operations
* Path traversal attempts are blocked

**Recommended Practice**:

* Run server with dedicated user account (not root)
* Limit file system access to specific directories
* Use read-only mounts for waveform file directories

Command Injection Protection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Viewer Launch**:

* Commands use list form (not shell strings)
* No ``shell=True`` in subprocess calls
* Viewer executables validated before launch

**File Monitoring**:

* File paths sanitized before operations
* No user-controlled command execution

Network Security
^^^^^^^^^^^^^^^^

**MCP Protocol**:

* Communication via stdin/stdout (not network sockets)
* No network exposure by default
* Client authentication handled by MCP client

**Deployment**:

* If exposing via network proxy, use TLS/SSL
* Implement authentication at proxy level
* Rate limiting recommended

Monitoring
----------

Logging
^^^^^^^

Configure logging levels::

    import logging
    logging.basicConfig(level=logging.INFO)

Log important events:

* Session creation and cleanup
* File operations (open, export, monitor)
* Error conditions
* Performance metrics

Health Checks
^^^^^^^^^^^^^

Implement health check endpoint (custom integration)::

    {
      "status": "healthy",
      "active_sessions": 3,
      "uptime_seconds": 86400,
      "memory_usage_mb": 512
    }

Metrics to Monitor
^^^^^^^^^^^^^^^^^^

* **Session Count**: Current active sessions
* **Memory Usage**: RAM consumption per session
* **Response Times**: Tool call latency
* **Error Rates**: Failed operations per hour
* **Disk Space**: Available space for exports

Troubleshooting
---------------

Common Issues
^^^^^^^^^^^^^

**Server Won't Start**:

* Check Python version (3.10+ required)
* Verify dependencies installed: ``pip list | grep mcp``
* Check for conflicting packages

**Session Timeout Errors**:

* Increase ``session_timeout`` in configuration
* Check for long-running operations
* Verify session IDs are valid

**File Access Errors**:

* Verify file paths are absolute
* Check directory permissions
* Ensure disk space available

**Viewer Launch Failures**:

* Verify viewer installed: ``which gtkwave``
* Check viewer in PATH
* Test viewer manually first

**Memory Issues**:

* Reduce ``max_sessions``
* Close unused sessions
* Limit signal cache size
* Use time range filtering

Debug Mode
^^^^^^^^^^

Enable detailed logging::

    export PYWELLEN_LOG_LEVEL=DEBUG
    pywellen-mcp

Check server status::

    # List active sessions
    waveform_list_sessions

    # Check file permissions
    ls -la /path/to/waveform/files

Performance Debugging
^^^^^^^^^^^^^^^^^^^^^

Run performance benchmarks::

    python scripts/benchmark.py

Profile memory usage::

    python -m memory_profiler your_script.py

Backup and Recovery
-------------------

Session State
^^^^^^^^^^^^^

Sessions are transient (in-memory only):

* No persistent state to backup
* Sessions recreated by opening waveforms
* Configuration files should be backed up

Configuration Backup
^^^^^^^^^^^^^^^^^^^^

Backup these files:

* ``config.json`` - Server configuration
* Signal list configurations (``.json``, ``.yaml``)
* GTKWave save files (``.gtkw``)
* Custom scripts and integrations

Disaster Recovery
^^^^^^^^^^^^^^^^^

1. **Server Failure**: Restart server, sessions will be recreated
2. **File Loss**: Restore waveform files from backup
3. **Configuration Loss**: Restore config files from backup
4. **Data Corruption**: Re-export from original waveforms

Upgrading
---------

Version Compatibility
^^^^^^^^^^^^^^^^^^^^^

* **Minor versions** (1.0 → 1.1): Backward compatible
* **Major versions** (1.0 → 2.0): May have breaking changes
* Review CHANGELOG before upgrading

Upgrade Process
^^^^^^^^^^^^^^^

1. **Backup Configuration**::

       cp config.json config.json.backup

2. **Install New Version**::

       pip install --upgrade pywellen-mcp

3. **Test in Development**::

       pywellen-mcp --version
       # Run integration tests

4. **Deploy to Production**::

       # Stop old version
       # Start new version
       # Verify functionality

5. **Rollback if Needed**::

       pip install pywellen-mcp==1.0.0

Best Practices
--------------

1. **Resource Management**:
   
   * Set appropriate session limits
   * Monitor memory usage
   * Clean up exports regularly

2. **Security**:
   
   * Run with minimal privileges
   * Validate all file paths
   * Keep dependencies updated

3. **Monitoring**:
   
   * Log important events
   * Track performance metrics
   * Set up alerts for errors

4. **Maintenance**:
   
   * Regular dependency updates
   * Periodic security audits
   * Performance benchmarking

5. **Documentation**:
   
   * Document custom configurations
   * Maintain runbooks
   * Track known issues

Support
-------

* **Documentation**: https://fvutils.github.io/pywellen-mcp
* **Issues**: https://github.com/fvutils/pywellen-mcp/issues
* **Discussions**: https://github.com/fvutils/pywellen-mcp/discussions

See Also
--------

* :doc:`getting_started` - Quick start guide
* :doc:`api_reference` - Complete API documentation
* :doc:`performance` - Performance tuning guide
* :doc:`security` - Security best practices
