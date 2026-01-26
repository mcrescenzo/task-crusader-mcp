"""
Service Executor - Direct service layer execution for MCP tools.

This module replaces CLI-based tool execution with direct service calls,
eliminating the overhead of subprocess spawning and CLI parsing.
"""

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

import yaml

from task_crusade_mcp.services import get_service_factory

logger = logging.getLogger(__name__)


class ServiceExecutor:
    """
    Executes MCP tool calls directly via service layer.

    This executor maps MCP tool names to service methods, providing
    direct service calls instead of CLI subprocess execution.
    """

    def __init__(self):
        """Initialize the service executor."""
        self._factory = get_service_factory()
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="mcp-service-")

        # Tool to service method mapping
        self._tool_handlers: Dict[str, callable] = {}
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register tool name to handler mappings."""
        # Campaign tools
        self._tool_handlers.update(
            {
                "campaign_create": self._handle_campaign_create,
                "campaign_list": self._handle_campaign_list,
                "campaign_show": self._handle_campaign_show,
                "campaign_update": self._handle_campaign_update,
                "campaign_delete": self._handle_campaign_delete,
                "campaign_get_progress_summary": self._handle_campaign_progress,
                "campaign_get_next_actionable_task": self._handle_next_actionable_task,
                "campaign_get_all_actionable_tasks": self._handle_all_actionable_tasks,
                "campaign_details": self._handle_campaign_details,
                "campaign_research_add": self._handle_campaign_research_add,
                "campaign_research_list": self._handle_campaign_research_list,
                "campaign_workflow_guide": self._handle_workflow_guide,
            }
        )

        # Task tools
        self._tool_handlers.update(
            {
                "task_create": self._handle_task_create,
                "task_list": self._handle_task_list,
                "task_show": self._handle_task_show,
                "task_update": self._handle_task_update,
                "task_delete": self._handle_task_delete,
                "task_complete": self._handle_task_complete,
                "task_acceptance_criteria_add": self._handle_add_criteria,
                "task_acceptance_criteria_mark_met": self._handle_criteria_met,
                "task_acceptance_criteria_mark_unmet": self._handle_criteria_unmet,
                "task_research_add": self._handle_add_research,
                "task_implementation_notes_add": self._handle_add_notes,
                "task_testing_step_add": self._handle_add_testing_step,
            }
        )

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Execute a tool and return YAML-formatted result.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments dictionary.

        Returns:
            YAML-formatted result string.
        """
        handler = self._tool_handlers.get(tool_name)
        if not handler:
            return self._format_error(f"Unknown tool: {tool_name}")

        try:
            # Run handler in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(self._executor, lambda: handler(arguments))
            return result
        except Exception as e:
            logger.error("Error executing tool %s: %s", tool_name, e, exc_info=True)
            return self._format_error(str(e))

    def _format_result(self, data: Any, success: bool = True) -> str:
        """Format result as YAML."""
        result = {
            "success": success,
            "data": data,
        }
        return yaml.dump(result, default_flow_style=False, allow_unicode=True)

    def _format_error(self, message: str, suggestions: Optional[list] = None) -> str:
        """Format error as YAML."""
        result = {
            "success": False,
            "error": message,
            "suggestions": suggestions or [],
        }
        return yaml.dump(result, default_flow_style=False, allow_unicode=True)

    # --- Campaign Handlers ---

    def _handle_campaign_create(self, args: Dict[str, Any]) -> str:
        """Handle campaign_create tool."""
        service = self._factory.get_campaign_service()
        result = service.create_campaign(
            name=args.get("name", ""),
            description=args.get("description"),
            priority=args.get("priority", "medium"),
            status=args.get("status", "planning"),
        )

        if result.is_success:
            return self._format_result(result.data)
        return self._format_error(result.error_message or "Failed to create campaign")

    def _handle_campaign_list(self, args: Dict[str, Any]) -> str:
        """Handle campaign_list tool."""
        service = self._factory.get_campaign_service()
        result = service.list_campaigns(
            status=args.get("status"),
            priority=args.get("priority"),
            limit=args.get("limit"),
        )

        if result.is_success:
            return self._format_result(result.data)
        return self._format_error(result.error_message or "Failed to list campaigns")

    def _handle_campaign_show(self, args: Dict[str, Any]) -> str:
        """Handle campaign_show tool."""
        service = self._factory.get_campaign_service()
        result = service.get_campaign_with_tasks(
            campaign_id=args.get("campaign_id", ""),
            include_task_details=args.get("verbosity", "standard") != "minimal",
        )

        if result.is_success:
            return self._format_result(result.data)
        return self._format_error(result.error_message or "Campaign not found")

    def _handle_campaign_update(self, args: Dict[str, Any]) -> str:
        """Handle campaign_update tool."""
        service = self._factory.get_campaign_service()
        campaign_id = args.pop("campaign_id", "")
        result = service.update_campaign(campaign_id, **args)

        if result.is_success:
            return self._format_result(result.data)
        return self._format_error(result.error_message or "Failed to update campaign")

    def _handle_campaign_delete(self, args: Dict[str, Any]) -> str:
        """Handle campaign_delete tool."""
        service = self._factory.get_campaign_service()
        result = service.delete_campaign(campaign_id=args.get("campaign_id", ""))

        if result.is_success:
            return self._format_result(result.data)
        return self._format_error(result.error_message or "Failed to delete campaign")

    def _handle_campaign_progress(self, args: Dict[str, Any]) -> str:
        """Handle campaign_get_progress_summary tool."""
        service = self._factory.get_campaign_service()
        result = service.get_progress_summary(campaign_id=args.get("campaign_id", ""))

        if result.is_success:
            return self._format_result(result.data)
        return self._format_error(result.error_message or "Failed to get progress")

    def _handle_next_actionable_task(self, args: Dict[str, Any]) -> str:
        """Handle campaign_get_next_actionable_task tool."""
        service = self._factory.get_campaign_service()
        result = service.get_next_actionable_task(
            campaign_id=args.get("campaign_id", ""),
            context_depth=args.get("context_depth", "basic"),
        )

        if result.is_success:
            return self._format_result(result.data)
        return self._format_error(result.error_message or "Failed to get next task")

    def _handle_all_actionable_tasks(self, args: Dict[str, Any]) -> str:
        """Handle campaign_get_all_actionable_tasks tool."""
        service = self._factory.get_campaign_service()
        result = service.get_all_actionable_tasks(
            campaign_id=args.get("campaign_id", ""),
            max_results=args.get("max_results", 10),
            context_depth=args.get("context_depth", "basic"),
        )

        if result.is_success:
            return self._format_result(result.data)
        return self._format_error(result.error_message or "Failed to get actionable tasks")

    def _handle_campaign_details(self, args: Dict[str, Any]) -> str:
        """Handle campaign_details tool."""
        service = self._factory.get_campaign_service()
        result = service.get_campaign(campaign_id=args.get("campaign_id", ""))

        if result.is_success:
            return self._format_result(result.data)
        return self._format_error(result.error_message or "Campaign not found")

    def _handle_campaign_research_add(self, args: Dict[str, Any]) -> str:
        """Handle campaign_research_add tool."""
        service = self._factory.get_campaign_service()
        result = service.add_campaign_research(
            campaign_id=args.get("campaign_id", ""),
            content=args.get("content", ""),
            research_type=args.get("research_type", "analysis"),
        )

        if result.is_success:
            return self._format_result(result.data)
        return self._format_error(result.error_message or "Failed to add research")

    def _handle_campaign_research_list(self, args: Dict[str, Any]) -> str:
        """Handle campaign_research_list tool."""
        service = self._factory.get_campaign_service()
        result = service.list_campaign_research(
            campaign_id=args.get("campaign_id", ""),
            research_type=args.get("research_type"),
        )

        if result.is_success:
            return self._format_result(result.data)
        return self._format_error(result.error_message or "Failed to list research")

    def _handle_workflow_guide(self, args: Dict[str, Any]) -> str:
        """Handle campaign_workflow_guide tool."""
        guide = {
            "title": "Task Crusade Workflow Guide",
            "phases": [
                {
                    "phase": "1. Planning",
                    "description": "Define campaign and tasks with dependencies",
                    "tools": ["campaign_create", "task_create", "task_acceptance_criteria_add"],
                },
                {
                    "phase": "2. Execution",
                    "description": "Work through tasks sequentially",
                    "pattern": [
                        "campaign_get_next_actionable_task(campaign_id) -> get next task",
                        "task_update(task_id, status='in-progress') -> claim task",
                        "[Implement the task]",
                        "task_acceptance_criteria_mark_met(criteria_id) -> mark criteria met",
                        "task_complete(task_id) -> complete task",
                        "Repeat until campaign complete",
                    ],
                },
                {
                    "phase": "3. Monitoring",
                    "description": "Track progress",
                    "tools": ["campaign_get_progress_summary", "campaign_show"],
                },
            ],
            "tips": [
                "Use campaign_get_next_actionable_task for sequential processing",
                "Use campaign_get_all_actionable_tasks for parallel execution",
                "Always mark criteria as met before completing a task",
            ],
        }
        return self._format_result(guide)

    # --- Task Handlers ---

    def _handle_task_create(self, args: Dict[str, Any]) -> str:
        """Handle task_create tool."""
        service = self._factory.get_task_service()

        # Parse acceptance_criteria if provided as JSON string
        criteria = args.get("acceptance_criteria")
        if isinstance(criteria, str):
            try:
                criteria = json.loads(criteria)
            except json.JSONDecodeError:
                criteria = [criteria]  # Treat as single criterion

        # Parse research if provided as JSON string
        research = args.get("research")
        if isinstance(research, str):
            try:
                research = json.loads(research)
            except json.JSONDecodeError:
                research = None

        result = service.create_task(
            title=args.get("title", ""),
            campaign_id=args.get("campaign_id", args.get("campaign", "")),
            description=args.get("description"),
            priority=args.get("priority", "medium"),
            status=args.get("status", "pending"),
            category=args.get("category"),
            task_type=args.get("type", "code"),
            dependencies=args.get("dependencies"),
            tags=args.get("tags"),
            acceptance_criteria=criteria,
            research_items=research,
        )

        if result.is_success:
            return self._format_result(result.data)
        return self._format_error(result.error_message or "Failed to create task")

    def _handle_task_list(self, args: Dict[str, Any]) -> str:
        """Handle task_list tool."""
        service = self._factory.get_task_service()
        result = service.list_tasks(
            campaign_id=args.get("campaign_id", args.get("campaign")),
            status=args.get("status"),
            priority=args.get("priority"),
            limit=args.get("limit"),
        )

        if result.is_success:
            return self._format_result(result.data)
        return self._format_error(result.error_message or "Failed to list tasks")

    def _handle_task_show(self, args: Dict[str, Any]) -> str:
        """Handle task_show tool."""
        service = self._factory.get_task_service()
        result = service.get_task(task_id=args.get("task_id", ""))

        if result.is_success:
            return self._format_result(result.data)
        return self._format_error(result.error_message or "Task not found")

    def _handle_task_update(self, args: Dict[str, Any]) -> str:
        """Handle task_update tool."""
        service = self._factory.get_task_service()
        task_id = args.pop("task_id", "")
        result = service.update_task(task_id, **args)

        if result.is_success:
            return self._format_result(result.data)
        return self._format_error(result.error_message or "Failed to update task")

    def _handle_task_delete(self, args: Dict[str, Any]) -> str:
        """Handle task_delete tool."""
        service = self._factory.get_task_service()
        result = service.delete_task(task_id=args.get("task_id", ""))

        if result.is_success:
            return self._format_result(result.data)
        return self._format_error(result.error_message or "Failed to delete task")

    def _handle_task_complete(self, args: Dict[str, Any]) -> str:
        """Handle task_complete tool."""
        service = self._factory.get_task_service()
        result = service.complete_task(task_id=args.get("task_id", ""))

        if result.is_success:
            return self._format_result(result.data)
        return self._format_error(
            result.error_message or "Failed to complete task",
            result.suggestions,
        )

    def _handle_add_criteria(self, args: Dict[str, Any]) -> str:
        """Handle task_acceptance_criteria_add tool."""
        service = self._factory.get_task_service()
        result = service.add_acceptance_criteria(
            task_id=args.get("task_id", ""),
            content=args.get("content", args.get("criterion", "")),
        )

        if result.is_success:
            return self._format_result(result.data)
        return self._format_error(result.error_message or "Failed to add criterion")

    def _handle_criteria_met(self, args: Dict[str, Any]) -> str:
        """Handle task_acceptance_criteria_mark_met tool."""
        service = self._factory.get_task_service()
        result = service.mark_criteria_met(
            criteria_id=args.get("criteria_id", args.get("criterion_id", "")),
        )

        if result.is_success:
            return self._format_result(result.data)
        return self._format_error(result.error_message or "Failed to mark criterion met")

    def _handle_criteria_unmet(self, args: Dict[str, Any]) -> str:
        """Handle task_acceptance_criteria_mark_unmet tool."""
        service = self._factory.get_task_service()
        result = service.mark_criteria_unmet(
            criteria_id=args.get("criteria_id", args.get("criterion_id", "")),
        )

        if result.is_success:
            return self._format_result(result.data)
        return self._format_error(result.error_message or "Failed to mark criterion unmet")

    def _handle_add_research(self, args: Dict[str, Any]) -> str:
        """Handle task_research_add tool."""
        service = self._factory.get_task_service()
        result = service.add_research(
            task_id=args.get("task_id", ""),
            content=args.get("content", ""),
            research_type=args.get("research_type", args.get("type", "findings")),
        )

        if result.is_success:
            return self._format_result(result.data)
        return self._format_error(result.error_message or "Failed to add research")

    def _handle_add_notes(self, args: Dict[str, Any]) -> str:
        """Handle task_implementation_notes_add tool."""
        service = self._factory.get_task_service()
        result = service.add_implementation_note(
            task_id=args.get("task_id", ""),
            content=args.get("content", args.get("note", "")),
        )

        if result.is_success:
            return self._format_result(result.data)
        return self._format_error(result.error_message or "Failed to add note")

    def _handle_add_testing_step(self, args: Dict[str, Any]) -> str:
        """Handle task_testing_step_add tool."""
        service = self._factory.get_task_service()
        result = service.add_testing_step(
            task_id=args.get("task_id", ""),
            content=args.get("content", ""),
            step_type=args.get("step_type", "verify"),
        )

        if result.is_success:
            return self._format_result(result.data)
        return self._format_error(result.error_message or "Failed to add testing step")

    def close(self) -> None:
        """Shutdown the executor."""
        self._executor.shutdown(wait=True)
