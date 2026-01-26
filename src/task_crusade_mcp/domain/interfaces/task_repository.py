"""Task Repository Interface."""

from typing import Any, Dict, List, Optional, Protocol

from task_crusade_mcp.domain.entities.result_types import DomainResult
from task_crusade_mcp.domain.entities.task import TaskDTO


class ITaskRepository(Protocol):
    """Protocol for task repository operations."""

    def create(self, task_data: Dict[str, Any]) -> DomainResult[TaskDTO]:
        """Create a new task."""
        ...

    def get(self, task_id: str) -> DomainResult[TaskDTO]:
        """Get task by ID."""
        ...

    def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> DomainResult[List[TaskDTO]]:
        """List tasks with optional filtering."""
        ...

    def update(self, task_id: str, updates: Dict[str, Any]) -> DomainResult[TaskDTO]:
        """Update a task."""
        ...

    def delete(self, task_id: str) -> DomainResult[Dict[str, Any]]:
        """Delete a task."""
        ...

    def get_by_campaign(
        self,
        campaign_id: str,
        status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> DomainResult[List[TaskDTO]]:
        """Get tasks for a campaign with optional status filter."""
        ...

    def get_actionable_tasks(
        self,
        campaign_id: str,
        max_results: int = 10,
    ) -> DomainResult[List[TaskDTO]]:
        """Get actionable tasks (dependencies met) for a campaign."""
        ...

    def get_next_actionable_task(
        self,
        campaign_id: str,
    ) -> DomainResult[Optional[TaskDTO]]:
        """Get the next actionable task for a campaign."""
        ...
