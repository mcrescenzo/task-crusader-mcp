"""Domain interfaces - Protocol-based repository contracts."""

from task_crusade_mcp.domain.interfaces.campaign_repository import ICampaignRepository
from task_crusade_mcp.domain.interfaces.memory_repository import (
    IMemoryAssociationRepository,
    IMemoryEntityRepository,
    IMemorySessionRepository,
)
from task_crusade_mcp.domain.interfaces.task_repository import ITaskRepository

__all__ = [
    "ICampaignRepository",
    "ITaskRepository",
    "IMemorySessionRepository",
    "IMemoryEntityRepository",
    "IMemoryAssociationRepository",
]
