"""Task MCP tool definitions."""

from typing import List

from mcp.types import Tool


def get_task_tools() -> List[Tool]:
    """Get task management MCP tools."""
    return [
        Tool(
            name="task_create",
            description="""Create a new task in a campaign.

Every task must belong to a campaign. Use campaign_list to find campaign IDs.

Parameters:
- title (required): Task title
- campaign_id (required): Campaign ID
- description (optional): Task description
- priority (optional): "low", "medium" (default), "high", or "critical"
- type (optional): "code", "research", "test", "documentation", etc.
- dependencies (optional): List of task IDs this task depends on
- acceptance_criteria (optional): List of acceptance criteria strings

Returns: Created task with ID.

RESPONSE FORMAT:
```yaml
success: true
data:
  id: <task-id>           # ← Task ID - use for task_update, task_complete, etc.
  title: Task title
  campaign_id: <campaign-id>
  status: pending
  priority: medium
  # ... other task fields ...
  acceptance_criteria_details:  # Only if acceptance_criteria provided
    - id: <criteria-id>    # ← Different from task ID
      content: Criterion text
      is_met: false
```

IMPORTANT:
- Extract task ID from `data.id` for subsequent operations
- Criteria IDs are at `data.acceptance_criteria_details[].id`

EXAMPLE:
```
result = task_create(title="Fix bug", campaign_id="camp-123")
task_id = result.data.id  # Use this ID
```""",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title"},
                    "campaign_id": {"type": "string", "description": "Campaign ID"},
                    "description": {"type": "string", "description": "Task description"},
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "description": "Task priority",
                    },
                    "type": {
                        "type": "string",
                        "enum": [
                            "code",
                            "research",
                            "test",
                            "documentation",
                            "refactor",
                            "deployment",
                            "review",
                        ],
                        "description": "Task type",
                    },
                    "dependencies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Task IDs this depends on",
                    },
                    "acceptance_criteria": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Acceptance criteria",
                    },
                },
                "required": ["title", "campaign_id"],
            },
        ),
        Tool(
            name="task_list",
            description="""List tasks with optional filtering.

Parameters:
- campaign_id (optional): Filter by campaign
- status (optional): Filter by status
- priority (optional): Filter by priority

Returns: List of tasks.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string", "description": "Filter by campaign"},
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in-progress", "blocked", "done", "cancelled"],
                        "description": "Filter by status",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "description": "Filter by priority",
                    },
                },
            },
        ),
        Tool(
            name="task_show",
            description="""Show detailed task information.

Returns task with acceptance criteria, research, implementation notes, and testing steps.

Parameters:
- task_id (required): Task ID

Returns: Task details with all associated data.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="task_update",
            description="""Update task properties.

Parameters:
- task_id (required): Task ID
- status (optional): New status
- priority (optional): New priority
- title (optional): New title
- description (optional): New description
- dependencies (optional): New list of task IDs this task depends on

Returns: Updated task.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in-progress", "blocked", "done", "cancelled"],
                        "description": "New status",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "description": "New priority",
                    },
                    "title": {"type": "string", "description": "New title"},
                    "description": {"type": "string", "description": "New description"},
                    "dependencies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Task IDs this depends on",
                    },
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="task_delete",
            description="""Delete a task permanently.

Parameters:
- task_id (required): Task ID to delete

Returns: Deletion confirmation.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID to delete"},
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="task_complete",
            description="""Mark a task as complete.

Validates that all acceptance criteria are met before completing.
If criteria are not met, returns an error with the unmet criteria.

Parameters:
- task_id (required): Task ID to complete

Returns: Completed task or error if criteria not met.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="task_acceptance_criteria_add",
            description="""Add an acceptance criterion to a task.

Acceptance criteria define the completion requirements for a task.
All criteria must be marked as met before the task can be completed.

Parameters:
- task_id (required): Task ID
- content (required): Criterion description

Returns: Created criterion with ID (use ID to mark as met).

RESPONSE FORMAT:
```yaml
success: true
data:
  id: <criteria-id>       # ← Use this ID for task_acceptance_criteria_mark_met
  content: Criterion text
  is_met: false
```""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "content": {"type": "string", "description": "Criterion description"},
                },
                "required": ["task_id", "content"],
            },
        ),
        Tool(
            name="task_acceptance_criteria_mark_met",
            description="""Mark an acceptance criterion as met.

Use this after completing work that satisfies the criterion.
Get criterion IDs from task_show or campaign_get_next_actionable_task.

Parameters:
- criteria_id (required): Criterion ID to mark as met

Returns: Updated criterion.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "criteria_id": {"type": "string", "description": "Criterion ID"},
                },
                "required": ["criteria_id"],
            },
        ),
        Tool(
            name="task_acceptance_criteria_mark_unmet",
            description="""Mark an acceptance criterion as not met.

Use this if a previously met criterion needs to be revisited.

Parameters:
- criteria_id (required): Criterion ID to mark as unmet

Returns: Updated criterion.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "criteria_id": {"type": "string", "description": "Criterion ID"},
                },
                "required": ["criteria_id"],
            },
        ),
        Tool(
            name="task_research_add",
            description="""Add a research item to a task.

Research types:
- findings: Investigation findings
- approaches: Implementation approaches
- docs: Documentation references

Parameters:
- task_id (required): Task ID
- content (required): Research content
- research_type (optional): Type of research (default: "findings")

Returns: Created research item.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "content": {"type": "string", "description": "Research content"},
                    "research_type": {
                        "type": "string",
                        "enum": ["findings", "approaches", "docs"],
                        "description": "Type of research",
                    },
                },
                "required": ["task_id", "content"],
            },
        ),
        Tool(
            name="task_implementation_notes_add",
            description="""Add an implementation note to a task.

Use this to document decisions, progress, blockers, or other implementation details.

Parameters:
- task_id (required): Task ID
- content (required): Note content

Returns: Created note.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "content": {"type": "string", "description": "Note content"},
                },
                "required": ["task_id", "content"],
            },
        ),
        Tool(
            name="task_testing_step_add",
            description="""Add a testing step to a task.

Testing steps provide verification guidance. Step types:
- setup: Environment setup
- trigger: Action to perform
- verify: Expected outcome verification
- cleanup: Cleanup steps
- debug: Troubleshooting and investigation
- fix: Corrective actions during testing
- iterate: Refinement and retesting cycles

Parameters:
- task_id (required): Task ID
- content (required): Step content
- step_type (optional): Type of step (default: "verify")

Returns: Created testing step.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "content": {"type": "string", "description": "Step content"},
                    "step_type": {
                        "type": "string",
                        "enum": [
                            "setup",
                            "trigger",
                            "verify",
                            "cleanup",
                            "debug",
                            "fix",
                            "iterate",
                        ],
                        "description": "Type of step",
                    },
                },
                "required": ["task_id", "content"],
            },
        ),
        # Phase 2: Search & Analytics tools
        Tool(
            name="task_search",
            description="""Full-text search across task titles and descriptions.

Parameters:
- query (required): Search query string
- campaign_id (optional): Filter by campaign
- status (optional): Filter by status
- priority (optional): Filter by priority
- limit (optional): Maximum results (default: 50)

Returns: Matching tasks with match information.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "campaign_id": {
                        "type": "string",
                        "description": "Filter by campaign",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in-progress", "blocked", "done", "cancelled"],
                        "description": "Filter by status",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "description": "Filter by priority",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results (default: 50)",
                        "default": 50,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="task_stats",
            description="""Get aggregate task statistics.

Returns statistics broken down by status, priority, type, and campaign.
Also includes acceptance criteria completion rates.

Parameters:
- campaign_id (optional): Filter by campaign

Returns: Task statistics summary.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {
                        "type": "string",
                        "description": "Filter by campaign",
                    },
                },
            },
        ),
        Tool(
            name="task_get_dependency_info",
            description="""Get dependency information for a task.

Returns upstream dependencies (blockers) and downstream dependents (tasks
that depend on this task).

Parameters:
- task_id (required): Task ID

Returns: Dependency graph information.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                },
                "required": ["task_id"],
            },
        ),
        # Phase 3: Bulk & Workflow tools
        Tool(
            name="task_bulk_update",
            description="""Update multiple tasks at once.

Parameters:
- task_ids (required): List of task IDs to update
- status (optional): New status for all tasks
- priority (optional): New priority for all tasks

Returns: Update summary with success/failure counts.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of task IDs to update",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in-progress", "blocked", "done", "cancelled"],
                        "description": "New status",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "description": "New priority",
                    },
                },
                "required": ["task_ids"],
            },
        ),
        Tool(
            name="task_create_from_template",
            description="""Create a task from a predefined template.

Templates include standard acceptance criteria and settings.

Available templates:
- bug-fix: Bug fix task with standard criteria
- feature: New feature implementation
- refactor: Code refactoring task
- research: Research and documentation task
- test: Testing task
- documentation: Documentation task

Parameters:
- template_name (required): Template name
- campaign_id (required): Campaign to create task in
- title (optional): Override title
- overrides (optional): JSON string of field overrides

Returns: Created task.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "template_name": {
                        "type": "string",
                        "enum": [
                            "bug-fix",
                            "feature",
                            "refactor",
                            "research",
                            "test",
                            "documentation",
                        ],
                        "description": "Template name",
                    },
                    "campaign_id": {"type": "string", "description": "Campaign ID"},
                    "title": {"type": "string", "description": "Override title"},
                    "overrides": {
                        "type": "string",
                        "description": "JSON string of field overrides",
                    },
                },
                "required": ["template_name", "campaign_id"],
            },
        ),
        Tool(
            name="task_complete_with_workflow",
            description="""Complete a task with full validation.

Validates before completing:
- All acceptance criteria are met
- All dependencies are completed
- Task is not already completed

Use this for strict workflow enforcement.

Parameters:
- task_id (required): Task ID

Returns: Completed task or validation errors.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                },
                "required": ["task_id"],
            },
        ),
        # Phase 4: Task Research CRUD
        Tool(
            name="task_research_list",
            description="""List all research items for a task.

Parameters:
- task_id (required): Task ID

Returns: List of research items.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="task_research_show",
            description="""Get a single research item by ID.

Parameters:
- task_id (required): Task ID
- research_id (required): Research item ID

Returns: Research item details.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "research_id": {"type": "string", "description": "Research ID"},
                },
                "required": ["task_id", "research_id"],
            },
        ),
        Tool(
            name="task_research_update",
            description="""Update a research item.

Parameters:
- task_id (required): Task ID
- research_id (required): Research item ID
- content (optional): New content
- research_type (optional): New type

Returns: Updated research item.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "research_id": {"type": "string", "description": "Research ID"},
                    "content": {"type": "string", "description": "New content"},
                    "research_type": {
                        "type": "string",
                        "enum": ["findings", "approaches", "docs"],
                        "description": "New type",
                    },
                },
                "required": ["task_id", "research_id"],
            },
        ),
        Tool(
            name="task_research_delete",
            description="""Delete a research item.

Parameters:
- task_id (required): Task ID
- research_id (required): Research item ID

Returns: Deletion confirmation.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "research_id": {"type": "string", "description": "Research ID"},
                },
                "required": ["task_id", "research_id"],
            },
        ),
        Tool(
            name="task_research_reorder",
            description="""Change research item order.

Parameters:
- task_id (required): Task ID
- research_id (required): Research item ID
- new_order (required): New order index (0-based)

Returns: Updated research item.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "research_id": {"type": "string", "description": "Research ID"},
                    "new_order": {"type": "integer", "description": "New order"},
                },
                "required": ["task_id", "research_id", "new_order"],
            },
        ),
        # Phase 5: Task Implementation Notes CRUD
        Tool(
            name="task_implementation_notes_list",
            description="""List all implementation notes for a task.

Parameters:
- task_id (required): Task ID

Returns: List of notes.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="task_implementation_notes_show",
            description="""Get a single implementation note by ID.

Parameters:
- task_id (required): Task ID
- note_id (required): Note ID

Returns: Note details.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "note_id": {"type": "string", "description": "Note ID"},
                },
                "required": ["task_id", "note_id"],
            },
        ),
        Tool(
            name="task_implementation_notes_update",
            description="""Update an implementation note.

Parameters:
- task_id (required): Task ID
- note_id (required): Note ID
- content (required): New content

Returns: Updated note.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "note_id": {"type": "string", "description": "Note ID"},
                    "content": {"type": "string", "description": "New content"},
                },
                "required": ["task_id", "note_id", "content"],
            },
        ),
        Tool(
            name="task_implementation_notes_delete",
            description="""Delete an implementation note.

Parameters:
- task_id (required): Task ID
- note_id (required): Note ID

Returns: Deletion confirmation.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "note_id": {"type": "string", "description": "Note ID"},
                },
                "required": ["task_id", "note_id"],
            },
        ),
        Tool(
            name="task_implementation_notes_reorder",
            description="""Change implementation note order.

Parameters:
- task_id (required): Task ID
- note_id (required): Note ID
- new_order (required): New order index (0-based)

Returns: Updated note.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "note_id": {"type": "string", "description": "Note ID"},
                    "new_order": {"type": "integer", "description": "New order"},
                },
                "required": ["task_id", "note_id", "new_order"],
            },
        ),
        # Phase 6: Task Acceptance Criteria CRUD
        Tool(
            name="task_acceptance_criteria_list",
            description="""List all acceptance criteria for a task.

Parameters:
- task_id (required): Task ID

Returns: List of criteria with met/unmet status.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="task_acceptance_criteria_show",
            description="""Get a single acceptance criterion by ID.

Parameters:
- task_id (required): Task ID
- criterion_id (required): Criterion ID

Returns: Criterion details.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "criterion_id": {"type": "string", "description": "Criterion ID"},
                },
                "required": ["task_id", "criterion_id"],
            },
        ),
        Tool(
            name="task_acceptance_criteria_update",
            description="""Update an acceptance criterion description.

Parameters:
- task_id (required): Task ID
- criterion_id (required): Criterion ID
- content (required): New content

Returns: Updated criterion.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "criterion_id": {"type": "string", "description": "Criterion ID"},
                    "content": {"type": "string", "description": "New content"},
                },
                "required": ["task_id", "criterion_id", "content"],
            },
        ),
        Tool(
            name="task_acceptance_criteria_delete",
            description="""Delete an acceptance criterion.

Parameters:
- task_id (required): Task ID
- criterion_id (required): Criterion ID

Returns: Deletion confirmation.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "criterion_id": {"type": "string", "description": "Criterion ID"},
                },
                "required": ["task_id", "criterion_id"],
            },
        ),
        Tool(
            name="task_acceptance_criteria_reorder",
            description="""Change acceptance criterion order.

Parameters:
- task_id (required): Task ID
- criterion_id (required): Criterion ID
- new_order (required): New order index (0-based)

Returns: Updated criterion.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "criterion_id": {"type": "string", "description": "Criterion ID"},
                    "new_order": {"type": "integer", "description": "New order"},
                },
                "required": ["task_id", "criterion_id", "new_order"],
            },
        ),
        # Phase 7: Task Testing Strategy CRUD
        Tool(
            name="task_testing_strategy_add",
            description="""Add a testing step to a task.

Alias for task_testing_step_add with additional step types support.

Parameters:
- task_id (required): Task ID
- content (required): Step description
- step_type (optional): Type of step

Returns: Created testing step.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "content": {"type": "string", "description": "Step content"},
                    "step_type": {
                        "type": "string",
                        "enum": [
                            "setup", "trigger", "verify", "cleanup",
                            "debug", "fix", "iterate",
                        ],
                        "description": "Step type",
                    },
                },
                "required": ["task_id", "content"],
            },
        ),
        Tool(
            name="task_testing_strategy_list",
            description="""List all testing steps for a task.

Parameters:
- task_id (required): Task ID

Returns: List of testing steps with status.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="task_testing_strategy_show",
            description="""Get a single testing step by ID.

Parameters:
- task_id (required): Task ID
- step_id (required): Testing step ID

Returns: Testing step details.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "step_id": {"type": "string", "description": "Step ID"},
                },
                "required": ["task_id", "step_id"],
            },
        ),
        Tool(
            name="task_testing_strategy_update",
            description="""Update a testing step.

Parameters:
- task_id (required): Task ID
- step_id (required): Testing step ID
- content (optional): New content
- step_type (optional): New step type

Returns: Updated testing step.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "step_id": {"type": "string", "description": "Step ID"},
                    "content": {"type": "string", "description": "New content"},
                    "step_type": {
                        "type": "string",
                        "enum": [
                            "setup", "trigger", "verify", "cleanup",
                            "debug", "fix", "iterate",
                        ],
                        "description": "Step type",
                    },
                },
                "required": ["task_id", "step_id"],
            },
        ),
        Tool(
            name="task_testing_strategy_delete",
            description="""Delete a testing step.

Parameters:
- task_id (required): Task ID
- step_id (required): Testing step ID

Returns: Deletion confirmation.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "step_id": {"type": "string", "description": "Step ID"},
                },
                "required": ["task_id", "step_id"],
            },
        ),
        Tool(
            name="task_testing_strategy_mark_passed",
            description="""Mark a testing step as passed.

Parameters:
- task_id (required): Task ID
- step_id (required): Testing step ID

Returns: Updated testing step.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "step_id": {"type": "string", "description": "Step ID"},
                },
                "required": ["task_id", "step_id"],
            },
        ),
        Tool(
            name="task_testing_strategy_mark_failed",
            description="""Mark a testing step as failed.

Parameters:
- task_id (required): Task ID
- step_id (required): Testing step ID

Returns: Updated testing step.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "step_id": {"type": "string", "description": "Step ID"},
                },
                "required": ["task_id", "step_id"],
            },
        ),
        Tool(
            name="task_testing_strategy_mark_skipped",
            description="""Mark a testing step as skipped.

Parameters:
- task_id (required): Task ID
- step_id (required): Testing step ID

Returns: Updated testing step.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "step_id": {"type": "string", "description": "Step ID"},
                },
                "required": ["task_id", "step_id"],
            },
        ),
        Tool(
            name="task_testing_strategy_reorder",
            description="""Change testing step order.

Parameters:
- task_id (required): Task ID
- step_id (required): Testing step ID
- new_order (required): New order index (0-based)

Returns: Updated testing step.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "step_id": {"type": "string", "description": "Step ID"},
                    "new_order": {"type": "integer", "description": "New order"},
                },
                "required": ["task_id", "step_id", "new_order"],
            },
        ),
    ]
