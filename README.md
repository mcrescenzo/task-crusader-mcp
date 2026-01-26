# Task Crusade MCP

Your AI coding assistant's quest companion - campaign and task management via MCP.

## Overview

Task Crusade is a campaign and task management system designed for AI coding assistants. It provides a Model Context Protocol (MCP) server that enables AI agents like Claude, Cursor, and others to organize work into campaigns (projects) and tasks with:

- **Dependency tracking**: Tasks can depend on other tasks
- **Acceptance criteria**: Define completion requirements for each task
- **Progress monitoring**: Track campaign progress and find actionable tasks
- **Sequential & parallel execution**: Support for both single-agent and multi-agent workflows

## Installation

### Basic Installation (MCP Server only)

```bash
pip install task-crusade-mcp
```

### With CLI

```bash
pip install task-crusade-mcp[cli]
```

### With TUI

```bash
pip install task-crusade-mcp[tui]
```

### Full Installation

```bash
pip install task-crusade-mcp[all]
```

## Quick Start

### 1. Configure Your AI Assistant

Add to your MCP client configuration (e.g., Claude Desktop `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "task-crusade": {
      "command": "crusader-mcp"
    }
  }
}
```

Or for Cursor (`.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "task-crusade": {
      "command": "crusader-mcp"
    }
  }
}
```

### 2. Basic Workflow

1. **Create a campaign:**
   ```
   campaign_create(name="My Project")
   ```

2. **Add tasks:**
   ```
   task_create(title="Implement feature", campaign_id="...")
   ```

3. **Add acceptance criteria:**
   ```
   task_acceptance_criteria_add(task_id="...", content="Unit tests pass")
   ```

4. **Execute the task loop:**
   ```
   while campaign not complete:
       1. campaign_get_next_actionable_task(campaign_id) -> get next task
       2. task_update(task_id, status="in-progress") -> claim task
       3. [Implement the task]
       4. task_acceptance_criteria_mark_met(criteria_id) -> mark criteria met
       5. task_complete(task_id) -> complete task
   ```

## Available Tools

### Campaign Management (12 tools)

| Tool | Description |
|------|-------------|
| `campaign_create` | Create a new campaign |
| `campaign_list` | List all campaigns |
| `campaign_show` | Show campaign details with tasks |
| `campaign_update` | Update campaign properties |
| `campaign_delete` | Delete a campaign |
| `campaign_get_progress_summary` | Get lightweight progress summary |
| `campaign_get_next_actionable_task` | Get next task with dependencies met |
| `campaign_get_all_actionable_tasks` | Get all actionable tasks (for parallel execution) |
| `campaign_details` | Show campaign metadata |
| `campaign_research_add` | Add research to campaign |
| `campaign_research_list` | List campaign research |
| `campaign_workflow_guide` | Get workflow guidance |

### Task Management (12 tools)

| Tool | Description |
|------|-------------|
| `task_create` | Create a new task |
| `task_list` | List tasks |
| `task_show` | Show task details |
| `task_update` | Update task properties |
| `task_delete` | Delete a task |
| `task_complete` | Complete a task (validates criteria) |
| `task_acceptance_criteria_add` | Add acceptance criterion |
| `task_acceptance_criteria_mark_met` | Mark criterion as met |
| `task_acceptance_criteria_mark_unmet` | Mark criterion as unmet |
| `task_research_add` | Add research to task |
| `task_implementation_notes_add` | Add implementation note |
| `task_testing_step_add` | Add testing step |

## CLI Usage

```bash
# Create a campaign
crusader campaign create "My Project" --description "My awesome project"

# List campaigns
crusader campaign list

# Show campaign details
crusader campaign show <campaign-id>

# Create a task
crusader task create "Implement feature" --campaign <campaign-id>

# Show task details
crusader task show <task-id>

# Update task status
crusader task update <task-id> --status in-progress
```

## TUI Usage

```bash
crusader-tui
```

This opens an interactive terminal interface for browsing campaigns and tasks.

## Database

By default, Task Crusade stores data in `~/.crusader/database.db`. You can configure a custom path by setting the `CRUSADER_DB_PATH` environment variable.

## Architecture

Task Crusade follows a clean hexagonal architecture:

```
MCP Server → Service Layer → Repository Layer → SQLite Database
                  ↓
            Domain Layer (DTOs, Result Types)
```

Key design decisions:
- **Direct service calls**: MCP tools call services directly (no CLI subprocess overhead)
- **Result pattern**: All operations return `DomainResult` for explicit error handling
- **Memory system internal**: Acceptance criteria, research, and notes use an internal memory system but are not exposed as MCP tools

## Contributing

Contributions are welcome! Before pushing, run the CI checks locally:

```bash
./scripts/check_ci.sh
```

This runs:
1. Linting with `ruff check src/ tests/`
2. Tests with coverage: `pytest --cov --cov-fail-under=65`
3. Optional type checking: `mypy src/`

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## License

MIT License - see LICENSE file for details.
