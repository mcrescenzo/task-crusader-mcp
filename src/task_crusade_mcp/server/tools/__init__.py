"""MCP Tool definitions."""

from typing import List

from mcp.types import Tool

from task_crusade_mcp.server.tools.campaign_tools import get_campaign_tools
from task_crusade_mcp.server.tools.task_tools import get_task_tools


def get_all_tools() -> List[Tool]:
    """Get all available MCP tools."""
    tools = []
    tools.extend(get_campaign_tools())
    tools.extend(get_task_tools())
    return tools


__all__ = [
    "get_all_tools",
    "get_campaign_tools",
    "get_task_tools",
]
