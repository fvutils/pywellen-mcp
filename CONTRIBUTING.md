# Contributing to PyWellen MCP

Thank you for your interest in contributing to PyWellen MCP! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)

## Code of Conduct

This project adheres to a code of conduct that emphasizes:

- **Respect**: Treat all contributors with respect and professionalism
- **Inclusivity**: Welcome contributions from people of all backgrounds
- **Collaboration**: Work together constructively
- **Quality**: Maintain high standards for code and documentation

## Getting Started

### Prerequisites

- Python 3.10 or later
- Git
- Basic understanding of MCP (Model Context Protocol)
- Familiarity with waveform file formats (VCD, FST, GHW)

### Development Setup

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/pywellen-mcp.git
   cd pywellen-mcp
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install in development mode**:
   ```bash
   pip install -e ".[dev]"
   ```

4. **Verify installation**:
   ```bash
   pytest
   python -m pywellen_mcp.server --version
   ```

### Project Structure

```
pywellen-mcp/
├── src/pywellen_mcp/       # Source code
│   ├── server.py           # MCP server
│   ├── session.py          # Session management
│   └── tools_*.py          # Tool implementations
├── tests/                  # Test suite
│   └── unit/               # Unit tests
├── scripts/                # Utility scripts
├── docs/                   # Documentation (RST format)
└── .github/workflows/      # CI/CD pipelines
```

## Development Workflow

### 1. Create a Branch

Create a feature branch from `master`:

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test improvements

### 2. Make Changes

- Write clear, concise code following our coding standards
- Add tests for new functionality
- Update documentation as needed
- Keep commits atomic and well-described

### 3. Test Your Changes

Run the full test suite:

```bash
# All tests
pytest

# With coverage
pytest --cov=pywellen_mcp --cov-report=html

# Specific test file
pytest tests/unit/test_tools_signal.py

# Specific test function
pytest tests/unit/test_tools_signal.py::test_signal_get_value
```

### 4. Commit Changes

Write clear commit messages:

```bash
git add .
git commit -m "feat: add support for LXT2 waveform format"
```

Commit message format:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `test:` - Testing
- `refactor:` - Code refactoring
- `perf:` - Performance improvement
- `chore:` - Maintenance tasks

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Coding Standards

### Python Style

- **PEP 8**: Follow Python style guide
- **Black**: Use Black formatter (line length: 88)
- **Type Hints**: Include type annotations for all functions
- **Docstrings**: Use Google-style docstrings

Example:

```python
from typing import Optional, List
from pywellen_mcp.session import SessionManager

async def signal_get_value(
    session_manager: SessionManager,
    session_id: str,
    signal_path: str,
    time: str,
    format: str = "int"
) -> dict:
    """Get the value of a signal at a specific time.
    
    Args:
        session_manager: The session manager instance
        session_id: Unique session identifier
        signal_path: Full hierarchical path to signal
        time: Time value as string
        format: Value format (int, hex, bin, signed)
        
    Returns:
        Dictionary containing signal value and metadata
        
    Raises:
        ValueError: If session_id or signal_path is invalid
        KeyError: If signal not found in hierarchy
    """
    # Implementation
    pass
```

### Code Organization

- **One tool per function**: Each MCP tool is a standalone async function
- **Session parameter**: Pass `session_manager` as first parameter
- **Error handling**: Use structured error responses
- **Type safety**: Use `typing` module for complex types

### Error Handling

Return structured errors:

```python
return {
    "error": "SESSION_NOT_FOUND",
    "message": f"Session {session_id} not found",
    "context": {
        "session_id": session_id,
        "active_sessions": list(session_manager.sessions.keys())
    }
}
```

Common error codes:
- `FILE_NOT_FOUND` - Waveform file not found
- `SESSION_NOT_FOUND` - Invalid session ID
- `INVALID_PATH` - Invalid signal/scope path
- `PARSE_ERROR` - Waveform parsing error
- `INVALID_TIME` - Invalid time value
- `INVALID_FORMAT` - Invalid format specifier

## Testing

### Writing Tests

- **Unit tests**: Test individual functions in isolation
- **Mocking**: Use `unittest.mock` for external dependencies
- **Fixtures**: Use pytest fixtures for common test data
- **Coverage**: Aim for 80%+ code coverage

Example test:

```python
import pytest
from unittest.mock import Mock, MagicMock
from pywellen_mcp.session import SessionManager
from pywellen_mcp.tools_signal import signal_get_value

@pytest.fixture
def session_manager():
    """Create a mock session manager."""
    manager = Mock(spec=SessionManager)
    session = MagicMock()
    session.waveform = MagicMock()
    session.hierarchy = MagicMock()
    manager.get_session.return_value = session
    return manager

@pytest.mark.asyncio
async def test_signal_get_value_success(session_manager):
    """Test successful signal value retrieval."""
    # Setup
    session = session_manager.get_session.return_value
    session.waveform.get_signal_value.return_value = 42
    
    # Execute
    result = await signal_get_value(
        session_manager=session_manager,
        session_id="test-session",
        signal_path="top.clk",
        time="100"
    )
    
    # Assert
    assert result["value"] == 42
    assert result["signal_path"] == "top.clk"
    assert result["time"] == "100"
```

### Test Categories

1. **Unit Tests** (`tests/unit/`):
   - Test individual functions
   - Use mocks for dependencies
   - Fast execution (<1s)

2. **Integration Tests** (future):
   - Test with real waveform files
   - Test tool interactions
   - Slower execution (seconds)

3. **Performance Tests** (`scripts/benchmark.py`):
   - Measure operation performance
   - Track performance regressions
   - Generate reports

### Running Tests

```bash
# All tests
pytest

# Specific category
pytest tests/unit/

# With coverage
pytest --cov=pywellen_mcp --cov-report=html

# Parallel execution
pytest -n auto

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

## Documentation

### Documentation Format

- **reStructuredText**: Use `.rst` files in `docs/`
- **Sphinx**: Built with Sphinx documentation generator
- **API Docs**: Auto-generated from docstrings
- **Examples**: Include practical examples

### Building Documentation

```bash
# Install documentation dependencies
pip install -e ".[docs]"

# Build HTML documentation
cd docs
make html

# View documentation
open _build/html/index.html  # On macOS
# or
xdg-open _build/html/index.html  # On Linux
```

### Documentation Structure

```
docs/
├── index.rst              # Main documentation index
├── getting_started.rst    # Installation and quick start
├── api_reference.rst      # Complete API documentation
├── best_practices.rst     # Usage recommendations
├── deployment.rst         # Production deployment
└── contributing.rst       # This guide
```

### Writing Documentation

- **Clear**: Use simple, direct language
- **Examples**: Include code examples
- **Complete**: Cover all parameters and return values
- **Updated**: Keep in sync with code changes

## Pull Request Process

### Before Submitting

1. **Tests pass**: Ensure all tests pass locally
2. **Coverage**: Maintain or improve code coverage
3. **Documentation**: Update relevant documentation
4. **Commits**: Clean up commit history (squash if needed)
5. **Changelog**: Add entry to CHANGELOG.md (if applicable)

### PR Description

Include:
- **Summary**: Brief description of changes
- **Motivation**: Why is this change needed?
- **Testing**: How was this tested?
- **Breaking Changes**: Any backwards incompatible changes?
- **Screenshots**: If UI/output changes

Template:

```markdown
## Summary
Brief description of what this PR does

## Motivation
Why is this change needed? What problem does it solve?

## Changes
- Change 1
- Change 2
- Change 3

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass (if applicable)
- [ ] Manual testing performed

## Breaking Changes
None / Description of breaking changes

## Checklist
- [ ] Code follows project style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (if needed)
```

### Review Process

1. **Automated checks**: CI/CD pipeline must pass
2. **Code review**: At least one maintainer approval
3. **Testing**: Reviewer may test manually
4. **Discussion**: Address feedback and comments
5. **Merge**: Maintainer will merge when ready

### After Merge

- Delete your feature branch
- Monitor for any issues
- Respond to follow-up questions

## Release Process

### Versioning

We use [Semantic Versioning](https://semver.org/):
- **Major** (1.0.0): Breaking changes
- **Minor** (0.1.0): New features, backwards compatible
- **Patch** (0.0.1): Bug fixes

### Release Checklist

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Run full test suite
4. Build documentation
5. Create release tag: `v1.0.0`
6. Push tag to trigger CI/CD
7. Verify PyPI publication
8. Create GitHub release with notes

### Release Notes

Include:
- New features
- Bug fixes
- Breaking changes
- Deprecations
- Contributors

## Questions?

- **Documentation**: Read the [full documentation](https://fvutils.github.io/pywellen-mcp)
- **Discussions**: Ask in [GitHub Discussions](https://github.com/fvutils/pywellen-mcp/discussions)
- **Issues**: Report bugs in [GitHub Issues](https://github.com/fvutils/pywellen-mcp/issues)
- **Email**: Contact maintainers directly

## Thank You!

Your contributions make PyWellen MCP better for everyone. We appreciate your time and effort!

---

**Happy Contributing! 🎉**
