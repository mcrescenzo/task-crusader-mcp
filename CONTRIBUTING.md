# Contributing to Task Crusade MCP

Thank you for your interest in contributing to Task Crusade MCP! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Development Setup](#development-setup)
- [Code Quality Standards](#code-quality-standards)
- [Running Tests](#running-tests)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)
- [Feature Requests](#feature-requests)
- [Code of Conduct](#code-of-conduct)

## Development Setup

### Prerequisites

- Python 3.10 or higher
- pip and virtualenv

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/mcrescenzo/task-crusader-mcp.git
   cd task-crusader-mcp
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install development dependencies:
   ```bash
   pip install -e .[dev]
   ```

4. Verify installation:
   ```bash
   pytest
   ```

## Code Quality Standards

We maintain high code quality standards to ensure reliability and maintainability.

### Coverage Requirements

- **Minimum test coverage**: 65% (enforced in CI)
- Note: Core MCP server coverage is 65%. Target excludes optional TUI/CLI (v0.1.0)
- Target coverage for new code: >85%
- All public APIs must have tests

### Code Formatting

We use several tools to maintain code quality:

```bash
# Format code with Black
black src/ tests/

# Sort imports with isort
isort src/ tests/

# Lint with ruff
ruff check src/ tests/

# Type check with mypy
mypy src/
```

**Before submitting a PR**, ensure all checks pass:

```bash
# Run all quality checks
black --check src/ tests/
isort --check src/ tests/
ruff check src/ tests/
mypy src/
pytest --cov --cov-fail-under=76
```

### Code Style

- Follow PEP 8 guidelines
- Line length: 100 characters
- Use type hints for all function signatures
- Write docstrings for public APIs using Google style
- Keep functions focused and single-purpose

## Running Tests

### All Tests

```bash
pytest
```

### With Coverage Report

```bash
pytest --cov --cov-report=html
# Open htmlcov/index.html to view coverage
```

### Specific Test Files

```bash
# Run unit tests
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run a specific test
pytest tests/unit/test_services/test_campaign_service.py::test_create_campaign -v
```

### Test Categories

Tests are marked with the following categories:
- `unit`: Unit tests for individual components
- `integration`: Integration tests for component interactions
- `database`: Tests requiring database access
- `e2e`: End-to-end workflow tests

Run specific categories:
```bash
pytest -m unit
pytest -m integration
```

## Pull Request Process

1. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make Your Changes**
   - Write clear, focused commits
   - Include tests for new functionality
   - Update documentation as needed
   - Follow the code quality standards

3. **Test Your Changes**
   ```bash
   # Run all tests
   pytest

   # Ensure coverage meets requirements
   pytest --cov --cov-fail-under=76

   # Run code quality checks
   ruff check src/ tests/
   mypy src/
   ```

4. **Update CHANGELOG.md**
   - Add your changes to the `[Unreleased]` section
   - Use appropriate category: Added, Changed, Deprecated, Removed, Fixed, Security

5. **Submit Pull Request**
   - Provide a clear description of changes
   - Reference any related issues
   - Ensure CI checks pass
   - Request review from maintainers

### PR Checklist

- [ ] Tests added/updated and passing
- [ ] Code coverage maintained at ≥65%
- [ ] Code formatted with black and isort
- [ ] Linting passes with ruff
- [ ] Type checking passes with mypy
- [ ] CHANGELOG.md updated
- [ ] Documentation updated if needed
- [ ] Commit messages are clear and descriptive

## Reporting Bugs

### Before Submitting a Bug Report

- Check existing issues to avoid duplicates
- Verify the bug in the latest version
- Collect relevant information

### Bug Report Template

```markdown
**Describe the bug**
A clear description of the bug.

**To Reproduce**
Steps to reproduce:
1. Create campaign with...
2. Add task with...
3. See error

**Expected behavior**
What you expected to happen.

**Actual behavior**
What actually happened.

**Environment**
- OS: [e.g., Ubuntu 22.04]
- Python version: [e.g., 3.11]
- Task Crusade MCP version: [e.g., 0.1.0]

**Additional context**
Error messages, logs, screenshots, etc.
```

## Feature Requests

We welcome feature requests! Please provide:

1. **Use Case**: Describe the problem you're trying to solve
2. **Proposed Solution**: Your suggested implementation
3. **Alternatives**: Other solutions you've considered
4. **Additional Context**: Examples, mockups, or references

## Architecture Overview

Task Crusade MCP follows hexagonal architecture:

```
MCP Server → Service Layer → Repository Layer → SQLite Database
                  ↓
            Domain Layer (DTOs, Result Types)
```

### Key Components

- **Domain Layer** (`domain/`): DTOs and result types
- **Database Layer** (`database/`): SQLAlchemy models and repositories
- **Service Layer** (`services/`): Business logic
- **Server Layer** (`server/`): MCP protocol implementation
- **CLI** (`cli/`): Command-line interface (optional)
- **TUI** (`tui/`): Text user interface (optional)

## Development Workflow

### Typical Development Cycle

1. Pick an issue or create one
2. Discuss approach with maintainers
3. Create feature branch
4. Implement changes with tests
5. Run quality checks locally
6. Submit PR
7. Address review feedback
8. Merge when approved

### Working with the Database

```bash
# The database is automatically created at ~/.crusader/database.db
# For testing, each test uses an isolated temporary database

# To reset your development database:
rm ~/.crusader/database.db
# It will be recreated on next run
```

### Entry Points

- `crusader-mcp`: MCP server (stdio transport)
- `crusader`: CLI (requires `[cli]` extra)
- `crusader-tui`: TUI (requires `[tui]` extra)

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive experience for everyone.

### Our Standards

**Examples of behavior that contributes to a positive environment:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**Examples of unacceptable behavior:**
- Harassment, discrimination, or derogatory comments
- Public or private harassment
- Publishing others' private information
- Other conduct which could reasonably be considered inappropriate

### Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported by contacting the project maintainers. All complaints will be reviewed and investigated promptly and fairly.

## Questions?

- Open a [GitHub Discussion](https://github.com/mcrescenzo/task-crusader-mcp/discussions) for questions
- Check the [README.md](README.md) for basic usage
- Check [DEVELOPMENT.md](DEVELOPMENT.md) for development commands

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
