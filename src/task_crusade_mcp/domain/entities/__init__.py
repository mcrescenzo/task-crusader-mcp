"""Domain entities - Data Transfer Objects."""

from task_crusade_mcp.domain.entities.campaign import CampaignDTO
from task_crusade_mcp.domain.entities.memory import (
    MemoryEntityDTO,
    MemorySessionDTO,
    MemoryTaskAssociationDTO,
)
from task_crusade_mcp.domain.entities.result_types import (
    DomainError,
    DomainErrorType,
    DomainResult,
    DomainSuccess,
)
from task_crusade_mcp.domain.entities.task import TaskDTO

__all__ = [
    "DomainError",
    "DomainErrorType",
    "DomainResult",
    "DomainSuccess",
    "CampaignDTO",
    "TaskDTO",
    "MemoryEntityDTO",
    "MemorySessionDTO",
    "MemoryTaskAssociationDTO",
]
