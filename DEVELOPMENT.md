# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Task Crusade MCP is a campaign and task management system designed for AI coding assistants. It provides an MCP (Model Context Protocol) server that enables AI agents to organize work into campaigns and tasks with dependency tracking, acceptance criteria, and progress monitoring.

## Development Commands

```bash
# Install for development
pip install -e .[dev]

# Run tests with coverage (85% coverage required)
pytest

# Run a single test file
pytest tests/unit/test_services/test_campaign_service.py

# Run a single test
pytest tests/unit/test_services/test_campaign_service.py::test_function_name -v

# Format code
black src/
isort src/

# Type check
mypy src/

# Run MCP server directly
crusader-mcp
```

## Architecture

The project follows a hexagonal architecture with clear separation of concerns:

```
MCP Server → Service Layer → Repository Layer → SQLite Database
                  ↓
            Domain Layer (DTOs, Result Types)
```

### Key Layers

**Domain Layer** (`domain/entities/`): Contains Data Transfer Objects (DTOs) and the `DomainResult` pattern for error handling. All service operations return `DomainResult[T]` with explicit success/failure handling via `DomainSuccess.create()` and `DomainError.*()` factory methods.

**Database Layer** (`database/`): SQLAlchemy models (`models/`) and repository implementations (`repositories/`). Uses `ORMManager` singleton for database connections.

**Service Layer** (`services/`): Business logic via `CampaignService` and `TaskService`. Services are created via `ServiceFactory` which handles dependency injection and caching.

**Server Layer** (`server/`): MCP server implementation. Tools are defined in `tools/campaign_tools.py` and `tools/task_tools.py`. The `ServiceExecutor` routes tool calls to services.

### Dependency Injection

`ServiceFactory` (singleton via `get_service_factory()`) creates and caches services and repositories. Services receive repository dependencies through constructor injection.

### Testing Patterns

Tests use temporary SQLite databases. Key fixtures in `conftest.py`:
- `reset_singletons` (autouse): Resets `ORMManager` and `ServiceFactory` before each test
- `orm_manager`: Creates `ORMManager` with temp database
- `campaign_service`, `task_service`: Fully wired services for testing

### Entry Points

- `crusader-mcp`: MCP server (stdio transport)
- `crusader`: CLI (requires `[cli]` optional dep)
- `crusader-tui`: TUI (requires `[tui]` optional dep)

### Environment Variables

- `CRUSADER_DB_PATH`: Custom database path (default: `~/.crusader/database.db`)
- `CRUSADER_DEBUG`: Enable debug logging (`1`, `true`, or `yes`)
