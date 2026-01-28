"""Campaign MCP tool definitions."""

from typing import List

from mcp.types import Tool


def get_campaign_tools() -> List[Tool]:
    """Get campaign management MCP tools."""
    return [
        Tool(
            name="campaign_create",
            description="""Create a new campaign to organize related tasks.

Campaigns are containers that group related tasks. Every task must belong to a campaign.

Parameters:
- name (required): Unique campaign name
- description (optional): Campaign description
- priority (optional): "low", "medium" (default), or "high"

Returns: Created campaign with ID.

RESPONSE FORMAT:
```yaml
success: true
data:
  id: <campaign-id>       # ← Campaign ID - use for task_create, campaign_update, etc.
  name: Campaign name
  status: planning
  priority: medium
  # ... other campaign fields ...
```

IMPORTANT: Extract campaign ID from `data.id` for subsequent operations.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Campaign name (unique)"},
                    "description": {"type": "string", "description": "Campaign description"},
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Campaign priority",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="campaign_list",
            description="""List all campaigns with optional filters.

Parameters:
- status (optional): Filter by "planning", "active", "completed", or "cancelled"
- priority (optional): Filter by "low", "medium", or "high"

Returns: List of campaigns with task statistics.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["planning", "active", "completed", "cancelled"],
                        "description": "Filter by status",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Filter by priority",
                    },
                },
            },
        ),
        Tool(
            name="campaign_show",
            description="""Show detailed campaign information including all tasks.

Parameters:
- campaign_id (required): Campaign ID to show
- verbosity (optional): "minimal", "standard", or "detailed"

Returns: Campaign details with task list.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string", "description": "Campaign ID"},
                    "verbosity": {
                        "type": "string",
                        "enum": ["minimal", "standard", "detailed"],
                        "description": "Output verbosity",
                    },
                },
                "required": ["campaign_id"],
            },
        ),
        Tool(
            name="campaign_update",
            description="""Update campaign properties.

Parameters:
- campaign_id (required): Campaign ID to update
- status (optional): New status
- priority (optional): New priority
- name (optional): New name
- description (optional): New description

Returns: Updated campaign.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string", "description": "Campaign ID"},
                    "status": {
                        "type": "string",
                        "enum": ["planning", "active", "paused", "completed", "cancelled"],
                        "description": "New status",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "New priority",
                    },
                    "name": {"type": "string", "description": "New name"},
                    "description": {"type": "string", "description": "New description"},
                },
                "required": ["campaign_id"],
            },
        ),
        Tool(
            name="campaign_delete",
            description="""Delete a campaign and all its tasks.

WARNING: This is permanent and cannot be undone.

Parameters:
- campaign_id (required): Campaign ID to delete

Returns: Deletion confirmation.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string", "description": "Campaign ID to delete"},
                },
                "required": ["campaign_id"],
            },
        ),
        Tool(
            name="campaign_get_progress_summary",
            description="""Get lightweight progress summary for a campaign.

Optimized for frequent progress monitoring (<150ms).

Parameters:
- campaign_id (required): Campaign ID

Returns: Progress summary with task counts, completion rate, and current/next tasks.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string", "description": "Campaign ID"},
                },
                "required": ["campaign_id"],
            },
        ),
        Tool(
            name="campaign_get_next_actionable_task",
            description="""Get the next actionable task with all dependencies met.

WHEN TO USE THIS TOOL:
- Sequential task processing (work on one task at a time)
- Finding what to work on next
- For parallel work, use campaign_get_all_actionable_tasks instead

Returns the highest-priority pending or in-progress task where ALL
dependencies have status="done". A task is "actionable" when:
- Status is "pending" or "in-progress"
- ALL tasks in its dependencies list have status="done"
- Higher priority tasks are returned first

IMPORTANT: Returns acceptance_criteria_details with IDs for marking criteria met.

Parameters:
- campaign_id (required): Campaign ID
- context_depth (optional): "basic" (default) returns task with acceptance criteria,
                            "full" includes research items and implementation notes

WORKFLOW:
1. Call this to get next task
2. task_update(task_id, status="in-progress")
3. Work on the task
4. task_acceptance_criteria_mark_met for each criterion
5. task_complete(task_id)
6. Repeat from step 1

Related: campaign_get_all_actionable_tasks (parallel), campaign_get_progress_summary

Returns: Next task with criteria, progress summary, and execution guidance.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string", "description": "Campaign ID"},
                    "context_depth": {
                        "type": "string",
                        "enum": ["basic", "full"],
                        "description": "Context depth",
                        "default": "basic",
                    },
                },
                "required": ["campaign_id"],
            },
        ),
        Tool(
            name="campaign_get_all_actionable_tasks",
            description="""Get ALL actionable tasks for parallel execution.

Use this when multiple agents can work simultaneously. Returns all tasks ready
to be worked on (dependencies met).

Parameters:
- campaign_id (required): Campaign ID
- max_results (optional): Maximum tasks to return (default: 10, max: 50)
- context_depth (optional): Context level - "basic" (default) returns task data with acceptance criteria, "full" additionally includes research items and implementation notes

Returns: List of actionable tasks with coordination warnings.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string", "description": "Campaign ID"},
                    "max_results": {
                        "type": "integer",
                        "description": "Max tasks (default: 10)",
                        "default": 10,
                    },
                    "context_depth": {
                        "type": "string",
                        "enum": ["basic", "full"],
                        "description": "Context depth",
                        "default": "basic",
                    },
                },
                "required": ["campaign_id"],
            },
        ),
        Tool(
            name="campaign_details",
            description="""Show campaign metadata without full task details.

Faster alternative to campaign_show when you don't need task listings.

Parameters:
- campaign_id (required): Campaign ID

Returns: Campaign metadata and progress summary.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string", "description": "Campaign ID"},
                },
                "required": ["campaign_id"],
            },
        ),
        Tool(
            name="campaign_research_add",
            description="""Add a research item to a campaign.

Research types:
- strategy: Strategic decisions, overall approach
- analysis: Requirements analysis, feasibility
- requirements: High-level requirements

Parameters:
- campaign_id (required): Campaign ID
- content (required): Research content
- research_type (optional): "strategy", "analysis", or "requirements"

Returns: Created research item.

RESPONSE FORMAT:
```yaml
success: true
data:
  id: <research-id>
  content: Research text
  research_type: strategy
```""",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string", "description": "Campaign ID"},
                    "content": {"type": "string", "description": "Research content"},
                    "research_type": {
                        "type": "string",
                        "enum": ["strategy", "analysis", "requirements"],
                        "description": "Type of research",
                    },
                },
                "required": ["campaign_id", "content"],
            },
        ),
        Tool(
            name="campaign_research_list",
            description="""List research items for a campaign.

Parameters:
- campaign_id (required): Campaign ID
- research_type (optional): Filter by type

Returns: List of research items.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string", "description": "Campaign ID"},
                    "research_type": {
                        "type": "string",
                        "enum": ["strategy", "analysis", "requirements"],
                        "description": "Filter by type",
                    },
                },
                "required": ["campaign_id"],
            },
        ),
        Tool(
            name="campaign_workflow_guide",
            description="""Get comprehensive workflow guidance.

WHEN TO USE THIS TOOL:
- First time using the campaign/task system
- Need a refresher on the recommended workflow
- Unsure which tool to use for a specific operation

Returns step-by-step guidance for planning, creation, and execution phases.

KEY WORKFLOW SUMMARY:
1. PLANNING: campaign_create_with_tasks (bulk) OR campaign_create + task_create
2. VALIDATION: campaign_validate_readiness
3. EXECUTION: campaign_get_next_actionable_task → task_update → work →
   task_acceptance_criteria_mark_met → task_complete → repeat
4. MONITORING: campaign_get_progress_summary, campaign_overview

Related: campaign_create_with_tasks (recommended for new campaigns)""",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="campaign_create_with_tasks",
            description="""Create campaign AND all tasks in ONE atomic operation.

*** USE THIS FOR BULK TASK CREATION ***

WHEN TO USE THIS TOOL:
- Setting up a new campaign with multiple tasks
- Creating tasks with interdependencies
- Atomic setup: ALL succeed or ALL fail (no partial state)

This is the RECOMMENDED way to create campaigns with tasks. Much faster
than individual task_create calls and handles dependencies automatically.

Tasks reference each other using temp_id for dependencies before UUIDs
are assigned. Dependencies are validated for cycles and missing references.

Parameters:
- campaign_json (required): JSON string with campaign and tasks spec

JSON Format:
```json
{
  "campaign": {
    "name": "Project Name",
    "description": "...",
    "priority": "low|medium|high"
  },
  "tasks": [
    {
      "temp_id": "setup",
      "title": "Setup environment",
      "dependencies": [],
      "acceptance_criteria": ["criterion 1", "criterion 2"]
    },
    {
      "temp_id": "implement",
      "title": "Implement feature",
      "dependencies": ["setup"],
      "acceptance_criteria": ["All tests pass"]
    },
    {
      "temp_id": "test",
      "title": "Integration tests",
      "dependencies": ["implement"]
    }
  ]
}
```

DEPENDENCY RULES:
- Use temp_id strings to reference other tasks in the same batch
- Dependencies are validated: all referenced temp_ids must exist
- Circular dependencies are detected and rejected
- Task A depends on B means: A cannot start until B status = "done"

Returns: Campaign with all tasks, temp_id → UUID mapping, creation summary.

Related: campaign_create (without tasks), task_create (individual tasks),
         campaign_validate_readiness (verify campaign before execution)""",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_json": {
                        "type": "string",
                        "description": "JSON spec with campaign and tasks",
                    },
                },
                "required": ["campaign_json"],
            },
        ),
        Tool(
            name="campaign_overview",
            description="""Get comprehensive campaign overview.

Returns combined view of progress, recent activity, actionable tasks,
and research items in a single call.

Parameters:
- campaign_id (required): Campaign ID

Returns: Campaign details, progress summary, recent tasks, actionable tasks,
and research items.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string", "description": "Campaign ID"},
                },
                "required": ["campaign_id"],
            },
        ),
        Tool(
            name="campaign_get_state_snapshot",
            description="""Export full campaign state for backup or analysis.

Returns complete campaign data including all tasks with their acceptance
criteria, research items, and implementation notes.

Parameters:
- campaign_id (required): Campaign ID

Returns: Complete campaign state with all associated data.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string", "description": "Campaign ID"},
                },
                "required": ["campaign_id"],
            },
        ),
        Tool(
            name="campaign_validate_readiness",
            description="""Check if campaign is ready to start execution.

Validates:
- Campaign has tasks
- No circular dependencies
- All task dependencies reference existing tasks
- At least one task is actionable

Parameters:
- campaign_id (required): Campaign ID

Returns: Readiness status with any issues or warnings found.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string", "description": "Campaign ID"},
                },
                "required": ["campaign_id"],
            },
        ),
        Tool(
            name="campaign_research_show",
            description="""Get a single campaign research item by ID.

Parameters:
- campaign_id (required): Campaign ID
- research_id (required): Research item ID

Returns: Research item details.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string", "description": "Campaign ID"},
                    "research_id": {"type": "string", "description": "Research item ID"},
                },
                "required": ["campaign_id", "research_id"],
            },
        ),
        Tool(
            name="campaign_research_update",
            description="""Update a campaign research item.

Parameters:
- campaign_id (required): Campaign ID
- research_id (required): Research item ID
- content (optional): New content
- research_type (optional): New type ("strategy", "analysis", "requirements")

Returns: Updated research item.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string", "description": "Campaign ID"},
                    "research_id": {"type": "string", "description": "Research item ID"},
                    "content": {"type": "string", "description": "New content"},
                    "research_type": {
                        "type": "string",
                        "enum": ["strategy", "analysis", "requirements"],
                        "description": "New research type",
                    },
                },
                "required": ["campaign_id", "research_id"],
            },
        ),
        Tool(
            name="campaign_research_delete",
            description="""Delete a campaign research item.

Parameters:
- campaign_id (required): Campaign ID
- research_id (required): Research item ID

Returns: Deletion confirmation.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string", "description": "Campaign ID"},
                    "research_id": {"type": "string", "description": "Research item ID"},
                },
                "required": ["campaign_id", "research_id"],
            },
        ),
        Tool(
            name="campaign_research_reorder",
            description="""Change the order of a campaign research item.

Parameters:
- campaign_id (required): Campaign ID
- research_id (required): Research item ID
- new_order (required): New order index (0-based)

Returns: Updated research item with new order.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string", "description": "Campaign ID"},
                    "research_id": {"type": "string", "description": "Research item ID"},
                    "new_order": {
                        "type": "integer",
                        "description": "New order index (0-based)",
                    },
                },
                "required": ["campaign_id", "research_id", "new_order"],
            },
        ),
        Tool(
            name="campaign_renumber_tasks",
            description="""Renumber all tasks in a campaign sequentially.

Tasks are numbered based on their dependency order (topological sort).

Parameters:
- campaign_id (required): Campaign ID
- start_from (optional): Starting number (default: 1)

Returns: Renumbering summary with task numbers.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string", "description": "Campaign ID"},
                    "start_from": {
                        "type": "integer",
                        "description": "Starting number (default: 1)",
                        "default": 1,
                    },
                },
                "required": ["campaign_id"],
            },
        ),
    ]
