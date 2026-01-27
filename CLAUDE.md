# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Task Crusader MCP is a campaign and task management system designed for AI coding assistants. It provides a Model Context Protocol (MCP) server with 24 tools for organizing work into campaigns and tasks with dependency tracking, acceptance criteria, and progress monitoring.

**Key Interfaces:**
- **MCP Server** (`crusader-mcp`): stdio-based MCP server for AI assistants
- **CLI** (`crusader`): Command-line interface using Typer
- **TUI** (`crusader-tui`): Terminal UI using Textual

## Development Commands

### Build and Test
```bash
# Run all CI checks (required before pushing)
./scripts/check_ci.sh

# Run tests
pytest                                    # All tests
pytest tests/unit/                        # Unit tests only
pytest tests/integration/                 # Integration tests only
pytest -m database                        # Database tests only
pytest path/to/test.py::test_name -v     # Single test

# Run tests with coverage
pytest --cov --cov-report=html            # Generate HTML coverage report
pytest --cov --cov-fail-under=65          # Enforce minimum coverage (CI requirement)

# Linting and formatting
ruff check src/ tests/                    # Lint code
black src/ tests/                         # Format code
isort src/ tests/                         # Sort imports
mypy src/                                 # Type checking (optional)
```

### Package Management
```bash
# Install for development
pip install -e .[dev]

# Build package
python -m build

# Version is managed by setuptools-scm (git tags)
# The _version.py file is auto-generated - never edit it
```

### Database
```bash
# Database location: ~/.crusader/database.db
# Set custom path: export CRUSADER_DB_PATH=/path/to/db.db

# Reset development database
rm ~/.crusader/database.db  # Will be recreated on next run

# Migrations are automatic via Alembic on first run
# Tests use isolated temporary databases
```

### Running Entry Points
```bash
crusader-mcp                              # Start MCP server (stdio transport)
crusader campaign list                    # CLI example
crusader-tui                              # Launch TUI
```

## Architecture

Task Crusader follows **hexagonal (ports & adapters) architecture**:

```
┌─────────────────────────────────────────────────────────┐
│                    Entry Points                         │
│  MCP Server (stdio) │ CLI (Typer) │ TUI (Textual)      │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                   Service Layer                         │
│  CampaignService │ TaskService                          │
│  - Business logic and orchestration                     │
│  - Uses ServiceFactory for dependency injection         │
│  - Returns DomainResult<T> for all operations           │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                  Repository Layer                       │
│  CampaignRepository │ TaskRepository │ Memory*          │
│  - Data access abstraction                              │
│  - Returns domain DTOs (not ORM models)                 │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                   Database Layer                        │
│  ORMManager (singleton) │ SQLAlchemy Models             │
│  - SQLite database (~/.crusader/database.db)            │
│  - Automatic migrations via Alembic                     │
└─────────────────────────────────────────────────────────┘
```

### Critical Design Patterns

**1. Result Pattern (DomainResult<T>)**
- ALL service methods return `DomainResult<T>`
- Never raise exceptions for business logic failures
- Use `DomainSuccess.create(data)` for success
- Use `DomainError.not_found()`, `.validation_error()`, etc. for failures

```python
# Example
result = campaign_service.create_campaign(name="Test")
if result.is_success:
    campaign_id = result.data["id"]
else:
    error = result.error_message
```

**2. Dependency Injection via ServiceFactory**
- ServiceFactory is a **singleton** that creates and caches services
- All repositories and services share the same ORMManager instance
- Use `get_service_factory()` to access the singleton
- Test code uses `reset_service_factory()` for isolation

```python
from task_crusade_mcp.services import get_service_factory

factory = get_service_factory()
campaign_service = factory.get_campaign_service()
task_service = factory.get_task_service()
```

**3. MCP Server Design**
- **Direct service calls** - MCP tools call services directly (no CLI subprocess overhead)
- ServiceExecutor maps tool names to service methods
- Tools are defined in `server/tools/` and registered in `service_executor.py`
- All results are YAML-formatted for consistency

**4. Memory System (Internal)**
- Acceptance criteria, research, and implementation notes use an internal "memory" system
- Memory entities are NOT exposed as separate MCP tools
- They are attached to tasks/campaigns and returned in nested structures
- Three repository types: MemorySessionRepository, MemoryEntityRepository, MemoryAssociationRepository

## Package Structure

```
src/task_crusade_mcp/
├── domain/                   # Pure domain logic (no infrastructure)
│   └── entities/
│       ├── result_types.py   # DomainResult, DomainError, DomainSuccess
│       ├── campaign.py       # CampaignDTO
│       ├── task.py          # TaskDTO
│       └── memory.py        # Memory DTOs
├── database/
│   ├── models/              # SQLAlchemy ORM models
│   ├── repositories/        # Data access layer (returns DTOs)
│   └── orm_manager.py       # Database singleton
├── services/
│   ├── campaign_service.py  # Campaign business logic
│   ├── task_service.py      # Task business logic
│   └── service_factory.py   # Dependency injection
├── server/
│   ├── mcp_server.py        # MCP protocol implementation
│   ├── service_executor.py  # Maps tools to service methods
│   └── tools/               # Tool definitions
├── cli/                     # Typer CLI (optional)
└── tui/                     # Textual TUI (optional)
```

## Important Implementation Details

### Version Management
- Version is managed by **setuptools-scm** based on git tags
- `src/task_crusade_mcp/_version.py` is auto-generated - **never edit manually**
- The file is in .gitignore and regenerated on each build
- Fallback version in pyproject.toml is used when not in git repo

### Package Naming
- Package name on PyPI: `task-crusader-mcp`
- Python import name: `task_crusade_mcp` (underscores)
- MCP server name: `task-crusader-mcp` (in server initialization)
- Always use `task-crusader-mcp` in error messages and documentation

### Test Requirements
- Minimum coverage: 65% (enforced in CI)
- Test markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.database`
- Each test gets isolated database via `isolated_orm_manager` fixture
- Mock external dependencies, test business logic thoroughly

### Database Migrations
- Migrations live in `database/migrations/versions/`
- Alembic runs automatically on first database access
- Models extend `Base` from `database/models/base.py`
- Always use UUIDs for primary keys, generated via `uuid4()`

### Error Handling
- Service layer: Return DomainResult with typed errors
- Repository layer: Return DTOs or None (let service layer handle errors)
- MCP server: Catch all exceptions and return McpError
- CLI/TUI: Format DomainResult errors for user display

## Testing Patterns

```python
# Unit test example
def test_create_campaign(mock_campaign_repo):
    service = CampaignService(campaign_repo=mock_campaign_repo, ...)
    result = service.create_campaign(name="Test", description="Desc")

    assert result.is_success
    assert result.data["name"] == "Test"

# Integration test example (uses real database)
def test_campaign_with_tasks(isolated_orm_manager):
    factory = ServiceFactory(isolated_orm_manager)
    campaign_service = factory.get_campaign_service()
    task_service = factory.get_task_service()

    # Create campaign
    result = campaign_service.create_campaign(name="Test")
    campaign_id = result.data["id"]

    # Create task
    result = task_service.create_task(
        title="Task 1",
        campaign_id=campaign_id
    )

    assert result.is_success
```

## Common Workflows

### Adding a New MCP Tool

1. Define tool schema in `server/tools/<category>_tools.py`:
```python
Tool(
    name="tool_name",
    description="What it does",
    inputSchema={
        "type": "object",
        "properties": {"param": {"type": "string"}},
        "required": ["param"]
    }
)
```

2. Add handler in `server/service_executor.py`:
```python
def _handle_tool_name(self, args: Dict[str, Any]) -> str:
    service = self._factory.get_campaign_service()
    result = service.method_name(args["param"])

    if result.is_success:
        return self._format_result(result.data)
    else:
        return self._format_error(result.error_message)
```

3. Register in `_register_handlers()`:
```python
self._tool_handlers["tool_name"] = self._handle_tool_name
```

4. Add service method in appropriate service class
5. Add tests for service method and tool execution

### Adding a New Service Method

1. Implement in service class (returns `DomainResult<T>`)
2. Use repository methods for data access
3. Apply business logic validation
4. Return typed DomainResult (success or error)
5. Write unit tests with mocked repositories
6. Write integration tests with real database

### Modifying Database Schema

1. Edit ORM models in `database/models/`
2. Create Alembic migration: `alembic revision --autogenerate -m "description"`
3. Review generated migration in `database/migrations/versions/`
4. Test migration applies cleanly
5. Update DTOs in `domain/entities/` if needed
6. Update repository methods if needed

## Code Quality Standards

- **Line length**: 100 characters
- **Python version**: 3.10+ (type hints required)
- **Formatting**: Black + isort (profile="black")
- **Linting**: Ruff (select = ["E", "F", "I", "N", "W", "B", "C4", "SIM"])
- **Type hints**: Required for all function signatures (`disallow_untyped_defs = true`)
- **Docstrings**: Google style for public APIs

### Type Checking Exceptions
These modules have `ignore_errors = true` in mypy config:
- `database/models/*` (SQLAlchemy compatibility)
- `database/orm_manager` (SQLAlchemy compatibility)
- `database/repositories/*` (SQLAlchemy compatibility)
- `tui/*` (Textual framework compatibility)

## Release Process

1. Update CHANGELOG.md with version and changes
2. Commit changes
3. Create git tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
4. Push: `git push origin main --tags`
5. GitHub Actions automatically publishes to PyPI on tag push
6. Create GitHub release with changelog

## Environment Variables

- `CRUSADER_DB_PATH`: Custom database location (default: `~/.crusader/database.db`)
- `CRUSADER_DEBUG`: Enable debug logging (`1`, `true`, or `yes`)
