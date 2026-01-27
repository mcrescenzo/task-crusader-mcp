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
    ]
