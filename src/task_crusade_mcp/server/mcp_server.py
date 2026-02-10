"""
Crusader MCP Server Implementation.

This module provides the CrusaderMCPServer class that implements the Model Context Protocol
(MCP) server for Task Crusade. It uses direct service calls instead of CLI wrapping.
"""

import asyncio
import atexit
import logging
import os
from typing import Any, Dict, List

from mcp.server import Server
from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR, ErrorData, TextContent, Tool

from task_crusade_mcp.database.orm_manager import get_orm_manager
from task_crusade_mcp.server.error_sanitizer import sanitize_exception
from task_crusade_mcp.server.service_executor import ServiceExecutor
from task_crusade_mcp.server.tools import get_all_tools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _is_debug_mode() -> bool:
    """Check if debug mode is enabled."""
    return os.environ.get("CRUSADER_DEBUG", "").lower() in ("1", "true", "yes")


class CrusaderMCPServer:
    """
    MCP server implementation for Task Crusade.

    The CrusaderMCPServer provides a complete MCP server using direct service
    layer calls instead of CLI subprocess execution.
    """

    def __init__(self):
        """Initialize the Crusader MCP server."""
        # Create MCP Server instance
        self._server = Server(
            name="task-crusader-mcp",
            version="0.1.0",
            instructions="""OpenCode Tools - Task and Project Management System

OVERVIEW:
OpenCode Tools is a comprehensive task and project management system with two core domains:

1. CAMPAIGNS: Collections of related tasks for organizing work (projects, sprints, features)
2. TASKS: Individual units of work with status tracking, dependencies, and rich metadata

GETTING STARTED:

Basic Workflow:
1. Create a campaign: campaign_create(name="My Project")
2. Add tasks: task_create(title="Task 1", campaign_id="...")
3. Add acceptance criteria: task_acceptance_criteria_add(task_id="...", content="...")
4. Track progress: task_update(status="in-progress"), task_show
5. Add details: task_research_add, task_implementation_notes_add, task_acceptance_criteria_add
6. Complete work: task_acceptance_criteria_mark_met, task_complete(task_id)

TASK EXECUTION LOOP:
```
while campaign not complete:
    1. campaign_get_next_actionable_task(campaign_id) -> get next task
    2. task_update(task_id, status="in-progress") -> claim task
    3. [Implement the task]
    4. task_acceptance_criteria_mark_met(criteria_id) -> mark criteria met
    5. task_complete(task_id) -> complete task
```

KEY CONCEPTS:

- Every task MUST belong to a campaign
- Tasks can have: research, implementation notes, acceptance criteria, testing strategy
- Dependencies use AND logic (all must complete before dependent task is actionable)
- Use campaign_get_next_actionable_task to find tasks ready to work on

TOOL CATEGORIES:

Campaign Management (21 tools):
- campaign_create, campaign_list, campaign_show, campaign_update, campaign_delete
- campaign_create_with_tasks, campaign_details, campaign_overview
- campaign_get_progress_summary, campaign_get_next_actionable_task, campaign_get_all_actionable_tasks
- campaign_get_state_snapshot, campaign_validate_readiness, campaign_renumber_tasks
- campaign_workflow_guide
- campaign_research_add, campaign_research_list, campaign_research_show, campaign_research_update, campaign_research_delete, campaign_research_reorder

Task Management (44 tools):
- task_create, task_list, task_show, task_update, task_delete, task_complete
- task_search, task_stats, task_get_dependency_info
- task_bulk_update, task_create_from_template, task_complete_with_workflow
- task_bulk_add_research, task_bulk_add_details
- task_acceptance_criteria_add, task_acceptance_criteria_mark_met, task_acceptance_criteria_mark_unmet
- task_acceptance_criteria_list, task_acceptance_criteria_show, task_acceptance_criteria_update, task_acceptance_criteria_delete, task_acceptance_criteria_reorder
- task_research_add, task_research_list, task_research_show, task_research_update, task_research_delete, task_research_reorder
- task_implementation_notes_add, task_implementation_notes_list, task_implementation_notes_show, task_implementation_notes_update, task_implementation_notes_delete, task_implementation_notes_reorder
- task_testing_step_add, task_testing_strategy_add
- task_testing_strategy_list, task_testing_strategy_show, task_testing_strategy_update, task_testing_strategy_delete
- task_testing_strategy_mark_passed, task_testing_strategy_mark_failed, task_testing_strategy_mark_skipped, task_testing_strategy_reorder

TIPS:

- Use campaign_get_next_actionable_task for sequential processing
- Use campaign_get_all_actionable_tasks for parallel execution
- Always mark criteria as met before completing a task
- Use campaign_workflow_guide for detailed workflow guidance
- Use task_bulk_add_research for shared findings across tasks
- Use task_bulk_add_details for unique details per task
- Use campaign_list and task_list to find IDs before other operations
- Use task_search to find tasks by text when you don't know the ID
""",
        )

        # Create service executor
        self._service_executor = ServiceExecutor()

        # Initialize database
        logger.info("Initializing database...")
        try:
            self._orm_manager = get_orm_manager()
            health = self._orm_manager.perform_health_check()
            if health.get("healthy"):
                logger.info(
                    "Database initialized: %s tables",
                    health.get("table_count", 0),
                )
            else:
                logger.warning("Database health check failed: %s", health.get("error"))
        except Exception as e:
            logger.error("Failed to initialize database: %s", e, exc_info=True)
            raise RuntimeError(f"Database initialization failed: {e}") from e

        # Pre-cache tools
        logger.info("Pre-caching tools...")
        self._tools = get_all_tools()
        logger.info("Loaded %d tools", len(self._tools))

        # Register protocol handlers
        self._register_handlers()

        # Register cleanup handler
        atexit.register(self.cleanup)

        logger.info("CrusaderMCPServer initialized")

    def _register_handlers(self) -> None:
        """Register MCP protocol handlers."""

        @self._server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """Handle list_tools request."""
            if _is_debug_mode():
                logger.debug("Handling list_tools request")
            return self._tools

        @self._server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle call_tool request."""
            if _is_debug_mode():
                logger.debug("Handling call_tool: %s", name)

            try:
                result_text = await self._service_executor.execute_tool(name, arguments)

                if _is_debug_mode():
                    preview = result_text[:200] + "..." if len(result_text) > 200 else result_text
                    logger.debug("Tool result preview: %s", preview)

                return [TextContent(type="text", text=result_text)]

            except Exception as e:
                logger.error("Error executing tool '%s': %s", name, e, exc_info=True)

                error_data = ErrorData(
                    code=INTERNAL_ERROR,
                    message=sanitize_exception(e),
                    data={"tool_name": name},
                )
                raise McpError(error_data) from e

        logger.debug("MCP protocol handlers registered")

    async def run(self, read_stream: Any, write_stream: Any, initialization_options: Any) -> None:
        """Run the MCP server with the provided streams."""
        logger.info("Starting MCP server main loop")

        try:
            await self._server.run(read_stream, write_stream, initialization_options)
        except Exception as e:
            logger.error("Error in MCP server main loop: %s", e, exc_info=True)
            raise
        finally:
            logger.info("MCP server main loop ended")
            self.cleanup()

    def create_initialization_options(self) -> Any:
        """Create initialization options for the MCP server."""
        return self._server.create_initialization_options()

    def cleanup(self) -> None:
        """Cleanup resources on shutdown."""
        try:
            if hasattr(self, "_service_executor") and self._service_executor:
                self._service_executor.close()

            if hasattr(self, "_orm_manager") and self._orm_manager:
                self._orm_manager.close()

            logger.info("Cleanup complete")
        except Exception as e:
            logger.error("Error during cleanup: %s", e, exc_info=True)


async def run_server() -> None:
    """Run the MCP server with stdio transport."""
    from mcp.server.stdio import stdio_server

    server = CrusaderMCPServer()

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    """Entry point for the MCP server."""
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error("Server error: %s", e, exc_info=True)
        raise


if __name__ == "__main__":
    main()
