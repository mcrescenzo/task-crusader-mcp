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
            instructions="""Task Crusade - Your AI coding assistant's quest companion

OVERVIEW:
Task Crusade is a campaign and task management system designed for AI coding assistants.
It helps organize work into campaigns (projects) and tasks with dependency tracking,
acceptance criteria, and progress monitoring.

GETTING STARTED:

Basic Workflow:
1. Create a campaign: campaign_create(name="My Project")
2. Add tasks: task_create(title="Task 1", campaign_id="...")
3. Add acceptance criteria: task_acceptance_criteria_add(task_id="...", content="...")
4. Execute: Use the Task Execution Loop (see below)
5. Track progress: campaign_get_progress_summary(campaign_id="...")

TASK EXECUTION LOOP:
```
while campaign not complete:
    1. campaign_get_next_actionable_task(campaign_id) -> get next task
    2. task_update(task_id, status="in-progress") -> claim task
    3. [Implement the task]
    4. task_acceptance_criteria_mark_met(criteria_id) -> mark criteria met
    5. task_complete(task_id) -> complete task
```

TOOL CATEGORIES:

Campaign Management:
- campaign_create, campaign_list, campaign_show, campaign_update, campaign_delete
- campaign_get_progress_summary, campaign_get_next_actionable_task, campaign_get_all_actionable_tasks
- campaign_research_add, campaign_research_list

Task Management:
- task_create, task_list, task_show, task_update, task_delete, task_complete
- task_acceptance_criteria_add, task_acceptance_criteria_mark_met, task_acceptance_criteria_mark_unmet
- task_research_add, task_implementation_notes_add, task_testing_step_add

TIPS:
- Use campaign_get_next_actionable_task for sequential processing
- Use campaign_get_all_actionable_tasks for parallel execution
- Always mark criteria as met before completing a task
- Use campaign_workflow_guide for detailed workflow guidance
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
                    message=str(e),
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
