LLM Optimization Tools
======================

Overview
--------

The PyWellen MCP server includes specialized tools designed to optimize interaction with Large Language Models (LLMs). These tools provide:

* Natural language query interpretation
* Context-efficient signal summaries
* Signal relationship recommendations  
* Educational documentation and guidance

These tools help reduce token usage, improve response quality, and make waveform analysis more accessible to LLMs.

Tools
-----

query_natural_language
^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: Interpret natural language queries and suggest appropriate tool calls.

**Use Case**: When user queries are ambiguous or exploratory, use this tool to map intent to specific MCP operations.

**Parameters**:

* ``session_id`` (string, required): Active waveform session ID
* ``query`` (string, required): Natural language query
* ``max_results`` (integer, optional): Maximum suggestions to return (default: 10)

**Returns**:

* ``interpreted_intent``: What the user is trying to accomplish
* ``suggested_tools``: List of tool calls with parameters
* ``reasoning``: Explanation of why these tools were chosen
* ``example_usage``: How to execute the suggestions

**Example Usage**::

    {
        "session_id": "abc123",
        "query": "show me all clock signals"
    }

**Example Response**::

    {
        "interpreted_intent": "Find clock signals",
        "suggested_tools": [
            {
                "tool": "search_by_activity",
                "parameters": {
                    "session_id": "abc123",
                    "min_toggles": 100
                },
                "priority": "high"
            },
            {
                "tool": "hierarchy_search",
                "parameters": {
                    "session_id": "abc123",
                    "pattern": "clk",
                    "case_sensitive": false
                },
                "priority": "medium"
            }
        ],
        "reasoning": [
            "High-activity signals likely to be clocks",
            "Signal names containing 'clk' likely to be clocks"
        ]
    }

**Common Query Patterns**:

* "show me all clock signals" → ``search_by_activity`` + ``hierarchy_search``
* "find reset signals" → ``hierarchy_search`` with pattern "reset|rst"
* "what caused signal X to change" → ``debug_trace_causality``
* "compare signal A and B" → ``signal_compare``
* "find rising edges" → ``debug_find_transition`` with condition="rises"
* "show timeline of events" → ``debug_event_timeline``

signal_summarize
^^^^^^^^^^^^^^^^

**Purpose**: Generate concise summaries of signal behavior instead of returning raw data.

**Use Case**: Use this instead of ``signal_list_changes`` when you need high-level understanding without consuming excessive tokens.

**Parameters**:

* ``session_id`` (string, required): Active waveform session ID
* ``variable_path`` (string, required): Signal path (e.g., "top.cpu.state")
* ``max_changes`` (integer, optional): Maximum representative changes (default: 20)
* ``include_stats`` (boolean, optional): Include statistical analysis (default: true)

**Returns**:

* ``signal_name``: Signal path
* ``summary``: One-line description of behavior
* ``total_changes``: Total number of transitions
* ``statistics``: Toggle count, value range, activity metrics
* ``representative_changes``: Key transitions (sampled, not exhaustive)
* ``patterns``: Detected patterns (periodic, constant, high_activity, etc.)
* ``recommendations``: Suggested next steps for analysis

**Example Usage**::

    {
        "session_id": "abc123",
        "variable_path": "top.clk"
    }

**Example Response**::

    {
        "signal_name": "top.clk",
        "summary": "Signal 'top.clk' has 1000 transitions, periodic with period ~10.0 time units, 1000 toggles (likely a clock signal)",
        "total_changes": 1000,
        "statistics": {
            "toggle_count": 1000,
            "toggle_rate": 0.5,
            "unique_values": 2,
            "period": 10.0
        },
        "patterns": ["periodic", "binary_toggle", "high_activity", "likely_clock"],
        "recommendations": [
            "Use this signal for temporal reference",
            "Consider using debug_event_timeline with this clock"
        ],
        "truncated": true
    }

**Detected Patterns**:

* ``constant``: Signal never changes
* ``single_transition``: Only one change
* ``low_activity``: Fewer than 5 changes
* ``high_activity``: High toggle rate (> 0.1)
* ``periodic``: Regular interval between changes
* ``binary_toggle``: Only toggles between two values
* ``likely_clock``: High activity + periodic pattern

recommend_related_signals
^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: Recommend signals related to a given signal for deeper analysis.

**Use Case**: Help LLMs discover relevant signals without exploring the entire hierarchy.

**Parameters**:

* ``session_id`` (string, required): Active waveform session ID
* ``variable_path`` (string, required): Reference signal path
* ``max_recommendations`` (integer, optional): Maximum recommendations (default: 10)

**Returns**:

* ``reference_signal``: The input signal
* ``recommendations``: List of related signals with relevance scores (0-1)
* ``categories``: Recommendations grouped by relationship type
* ``total_recommendations``: Number of recommendations returned

**Relationship Categories**:

* ``same_scope``: Signals in the same module/scope (relevance: 0.8)
* ``similar_name``: Signals with similar naming patterns
* ``complementary``: Related by common patterns (clk/data, req/ack, wr/rd)
* ``control_flow``: Common control signals (valid, ready, enable, reset)

**Example Usage**::

    {
        "session_id": "abc123",
        "variable_path": "top.cpu.req"
    }

**Example Response**::

    {
        "reference_signal": "top.cpu.req",
        "recommendations": [
            {
                "path": "top.cpu.ack",
                "name": "ack",
                "relevance": 0.8,
                "reason": "In same scope",
                "category": "same_scope"
            },
            {
                "pattern": "*ack*",
                "relevance": 0.7,
                "reason": "Complementary to req signal",
                "category": "complementary"
            }
        ],
        "total_recommendations": 2
    }

**Complementary Signal Patterns**:

* ``clk`` → data, valid, enable
* ``req`` → ack, grant, ready
* ``write`` → read, data, addr
* ``valid`` → ready, data

docs_get_started
^^^^^^^^^^^^^^^^

**Purpose**: Get quick-start guide for using the PyWellen MCP server.

**Use Case**: When an LLM needs to understand available capabilities and common workflows.

**Parameters**: None

**Returns**:

* ``overview``: Brief description of the server
* ``quick_start``: Step-by-step getting started guide
* ``common_workflows``: Example task sequences
* ``tool_categories``: Tools organized by purpose
* ``tips``: Best practices for LLM interaction

**Common Workflows**:

1. **Debugging**:
   
   a. Open waveform with ``waveform_open``
   b. Find error signal with ``hierarchy_search``
   c. Get value at failure time with ``signal_get_value``
   d. Trace causes with ``debug_trace_causality``
   e. Build timeline with ``debug_event_timeline``

2. **Clock Analysis**:
   
   a. Find clocks with ``search_by_activity`` (high toggles)
   b. Or search with ``hierarchy_search`` pattern='clk'
   c. Summarize behavior with ``signal_summarize``
   d. Find edges with ``debug_find_transition`` condition='rises'

3. **Signal Comparison**:
   
   a. Find signals with ``hierarchy_search``
   b. Compare with ``signal_compare``
   c. Get specific values if differences found
   d. Build event timeline for both signals

4. **Design Exploration**:
   
   a. Get metadata with ``waveform_info``
   b. List top scopes with ``hierarchy_list_top_scopes``
   c. Drill down with ``hierarchy_get_scope``
   d. List variables with ``hierarchy_list_variables``
   e. Use ``recommend_related_signals`` for discovery

docs_tool_guide
^^^^^^^^^^^^^^^

**Purpose**: Get detailed usage guide for a specific tool.

**Use Case**: When an LLM needs in-depth documentation for how to use a particular tool.

**Parameters**:

* ``tool_name`` (string, required): Name of tool to document

**Returns**:

* ``tool_name``: Name of the tool
* ``description``: What the tool does
* ``parameters``: Detailed parameter descriptions
* ``returns``: What the tool returns
* ``examples``: Usage examples
* ``related_tools``: Other tools commonly used with this one
* ``common_errors``: Typical errors and solutions

**Example Usage**::

    {
        "tool_name": "signal_get_value"
    }

**Documented Tools**: waveform_open, signal_get_value, debug_trace_causality, signal_summarize

Best Practices
--------------

Token Efficiency
^^^^^^^^^^^^^^^^

1. **Use signal_summarize instead of signal_list_changes** for high-level understanding
2. **Use query_natural_language** to interpret ambiguous user requests
3. **Use recommend_related_signals** to discover signals without listing all
4. **Limit max_results** parameters to reduce response size

Query Interpretation Patterns
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When users ask:

* "Show me..." → Use ``hierarchy_search`` or ``hierarchy_list_variables``
* "What caused..." → Use ``debug_trace_causality``
* "Compare..." → Use ``signal_compare``
* "Find edges/transitions..." → Use ``debug_find_transition``
* "Timeline..." → Use ``debug_event_timeline``
* "Active signals..." → Use ``search_by_activity``

Context Window Management
^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Start with summaries, drill down to details only if needed
2. Use pagination (limit/offset) for large result sets
3. Truncate long outputs with max_results parameters
4. Group related operations in single requests
5. Close sessions when done to free resources

Integration with Workflows
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Natural Language → Tool Mapping:

1. Receive user's natural language request
2. Call ``query_natural_language`` to interpret intent
3. Review suggested tools and parameters
4. Execute the suggested tool calls
5. Present results to user in natural language

Limitations
-----------

* ``query_natural_language`` uses heuristics, not full NLP
* Parameter extraction (e.g., signal names, times) must be done by calling LLM
* Signal pattern detection is based on simple statistics, not deep analysis
* Complementary signal suggestions are based on naming conventions

See Also
--------

* :doc:`hierarchy_navigation` - For exploring design structure
* :doc:`signal_analysis` - For detailed signal queries
* :doc:`debugging_tools` - For debugging workflows
* :doc:`api_reference` - Complete API documentation
