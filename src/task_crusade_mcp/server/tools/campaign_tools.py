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

Returns: Created campaign with ID.""",
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
            description="""List all campaigns with optional status filter.

Parameters:
- status (optional): Filter by "planning", "active", "completed", or "cancelled"

Returns: List of campaigns with task statistics.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["planning", "active", "completed", "cancelled"],
                        "description": "Filter by status",
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

Use this for sequential task processing. Returns the highest-priority pending or
in-progress task with all dependencies in "done" status.

IMPORTANT: Returns acceptance_criteria_details with IDs for marking criteria met.

Parameters:
- campaign_id (required): Campaign ID
- context_depth (optional): "basic" (default) or "full"

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
- context_depth (optional): "basic" (default) or "full"

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

Returns: Created research item.""",
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

Call this first when starting to use the campaign/task system.
Returns step-by-step guidance for planning, creation, and execution phases.""",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]
