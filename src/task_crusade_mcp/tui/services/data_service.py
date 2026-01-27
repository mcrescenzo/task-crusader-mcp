# src/task_crusade_mcp/tui/services/data_service.py
"""TUI Data Service - Adapter between TUI widgets and application services.

This module provides the TUIDataService class that wraps synchronous service
calls with asyncio.to_thread() to provide non-blocking async methods
for the TUI. All TUI widgets use this service for data access.

Example usage:
    data_service = TUIDataService()
    campaigns = await data_service.get_campaigns(status="active")
    tasks = await data_service.get_tasks(campaign_id)
    task_detail = await data_service.get_task_detail(task_id)
"""

import asyncio
import logging
from typing import Any

from task_crusade_mcp.services import get_service_factory
from task_crusade_mcp.tui.constants import STATUS_CYCLE
from task_crusade_mcp.tui.exceptions import DataFetchError, DataUpdateError

logger = logging.getLogger(__name__)


class TUIDataService:
    """Adapter between TUI widgets and application services.

    This class provides async methods that wrap synchronous service
    calls using asyncio.to_thread() for non-blocking UI behavior. It transforms
    service results into widget-friendly dictionaries and raises appropriate
    exceptions on failures.

    Example:
        >>> service = TUIDataService()
        >>> campaigns = await service.get_campaigns()
        >>> tasks = await service.get_tasks(campaigns[0]["id"])
    """

    def __init__(self) -> None:
        """Initialize the data service."""
        pass  # Services are obtained via get_service_factory()

    def _get_campaign_service(self):
        """Get campaign service instance.

        Returns:
            CampaignService: Configured service instance.
        """
        factory = get_service_factory()
        return factory.get_campaign_service()

    def _get_task_service(self):
        """Get task service instance.

        Returns:
            TaskService: Configured service instance.
        """
        factory = get_service_factory()
        return factory.get_task_service()

    # =========================================================================
    # Campaign Operations
    # =========================================================================

    async def get_campaigns(self, status: str = "all") -> list[dict[str, Any]]:
        """Get campaigns for the campaign list widget.

        Args:
            status: Filter by campaign status. Options:
                - "all": Show all campaigns
                - "planning", "active", "paused", "completed", "cancelled": Filter by status

        Returns:
            List of campaign dictionaries with id, name, status, priority,
            task_count, and done_count.

        Raises:
            DataFetchError: If campaigns cannot be fetched from the service.
        """

        def _sync_get() -> list[dict[str, Any]]:
            service = self._get_campaign_service()

            # Handle "all" status by fetching all campaign statuses
            if status == "all":
                # Fetch campaigns from all statuses
                all_statuses = ["planning", "active", "paused", "completed", "cancelled"]
                campaigns: list[dict[str, Any]] = []

                for campaign_status in all_statuses:
                    result = service.list_campaigns(status=campaign_status)
                    if result.is_success:
                        campaigns.extend(result.data or [])
            else:
                result = service.list_campaigns(status=status)

                if result.is_failure:
                    raise DataFetchError(
                        "fetch campaigns",
                        result.error_message or "Unknown error",
                    )

                campaigns = result.data or []

            # Enrich campaigns with task counts
            enriched = []
            for c in campaigns:
                # Handle both dict and DTO-like objects
                campaign_data = c.to_dict() if hasattr(c, "to_dict") else c

                # Get task counts from progress summary
                campaign_id = campaign_data["id"]
                progress_result = service.get_progress_summary(campaign_id)
                task_count = 0
                done_count = 0

                if progress_result.is_success and progress_result.data:
                    progress = progress_result.data
                    task_count = progress.get("total_tasks", 0)
                    by_status = progress.get("tasks_by_status", {})
                    done_count = by_status.get("done", 0)

                enriched.append(
                    {
                        "id": campaign_data["id"],
                        "name": campaign_data["name"],
                        "status": campaign_data.get("status", "planning"),
                        "priority": campaign_data.get("priority", "medium"),
                        "task_count": task_count,
                        "done_count": done_count,
                    }
                )

            return enriched

        return await asyncio.to_thread(_sync_get)

    async def delete_campaign(self, campaign_id: str) -> bool:
        """Delete a campaign and all its tasks.

        Args:
            campaign_id: ID of the campaign to delete.

        Returns:
            True if deletion was successful.

        Raises:
            DataUpdateError: If campaign cannot be deleted.
        """

        def _sync_delete() -> bool:
            service = self._get_campaign_service()
            result = service.delete_campaign(campaign_id)
            if result.is_failure:
                raise DataUpdateError(
                    "delete campaign",
                    campaign_id,
                    result.error_message or "Unknown error",
                )
            return True

        return await asyncio.to_thread(_sync_delete)

    async def get_campaign_task_count(self, campaign_id: str) -> int:
        """Get task count for delete confirmation modal.

        Args:
            campaign_id: ID of the campaign.

        Returns:
            Number of tasks in the campaign.

        Raises:
            DataFetchError: If tasks cannot be fetched.
        """
        tasks = await self.get_tasks(campaign_id)
        return len(tasks)

    async def create_campaign(
        self, name: str, priority: str = "medium", description: str = ""
    ) -> dict[str, Any]:
        """Create a new campaign.

        Args:
            name: Campaign name.
            priority: Campaign priority (low/medium/high).
            description: Optional campaign description.

        Returns:
            Dictionary containing the created campaign data.

        Raises:
            DataUpdateError: If campaign cannot be created.
        """

        def _sync_create() -> dict[str, Any]:
            service = self._get_campaign_service()
            result = service.create_campaign(
                name=name,
                priority=priority,
                description=description if description else None,
            )
            if result.is_failure:
                raise DataUpdateError(
                    "create campaign",
                    "",
                    result.error_message or "Unknown error",
                )
            return result.data

        return await asyncio.to_thread(_sync_create)

    async def get_campaign_summary(self, campaign_id: str) -> dict[str, Any] | None:
        """Get campaign summary for the detail panel.

        Fetches campaign metadata, progress summary, and research items
        for display in the detail pane when no task is selected.

        Args:
            campaign_id: ID of the campaign to get summary for.

        Returns:
            Dictionary containing:
                - campaign: Campaign metadata (name, description, status, priority, etc.)
                - progress: Progress summary (total_tasks, tasks_by_status, completion_rate)
                - research: List of campaign-level research items
            Returns None if campaign not found.

        Raises:
            DataFetchError: If campaign summary cannot be fetched.
        """

        def _sync_get() -> dict[str, Any] | None:
            service = self._get_campaign_service()

            # Get campaign details
            campaign_result = service.get_campaign(campaign_id)
            if campaign_result.is_failure:
                raise DataFetchError(
                    "fetch campaign summary",
                    campaign_result.error_message or "Unknown error",
                )

            campaign_data = campaign_result.data
            if campaign_data is None:
                return None

            # Get progress summary
            progress_result = service.get_progress_summary(campaign_id)
            progress_data = progress_result.data if progress_result.is_success else {}

            # Get campaign research
            research_result = service.list_campaign_research(campaign_id)
            research_data = research_result.data if research_result.is_success else []

            return {
                "campaign": campaign_data,
                "progress": progress_data,
                "research": research_data,
            }

        return await asyncio.to_thread(_sync_get)

    # =========================================================================
    # Task Operations
    # =========================================================================

    async def create_task(
        self,
        campaign_id: str,
        title: str,
        priority: str = "medium",
        description: str = "",
    ) -> dict[str, Any]:
        """Create a new task in a campaign.

        Args:
            campaign_id: ID of the campaign to create the task in.
            title: Task title.
            priority: Task priority (low/medium/high/critical).
            description: Optional task description.

        Returns:
            Dictionary containing the created task data.

        Raises:
            DataUpdateError: If task cannot be created.
        """

        def _sync_create() -> dict[str, Any]:
            service = self._get_task_service()
            result = service.create_task(
                title=title,
                campaign_id=campaign_id,
                priority=priority,
                description=description if description else None,
            )
            if result.is_failure:
                raise DataUpdateError(
                    "create task",
                    "",
                    result.error_message or "Unknown error",
                )
            return result.data

        return await asyncio.to_thread(_sync_create)

    async def get_tasks(self, campaign_id: str) -> list[dict[str, Any]]:
        """Get tasks for the task list widget.

        Args:
            campaign_id: ID of the campaign to get tasks for.

        Returns:
            List of task dictionaries.

        Raises:
            DataFetchError: If tasks cannot be fetched from the service.
        """

        def _sync_get() -> list[dict[str, Any]]:
            service = self._get_task_service()
            result = service.list_tasks(campaign_id=campaign_id)

            if result.is_failure:
                raise DataFetchError(
                    "fetch tasks",
                    result.error_message or "Unknown error",
                )

            tasks = result.data or []
            return tasks

        return await asyncio.to_thread(_sync_get)

    async def get_task_detail(self, task_id: str) -> dict[str, Any] | None:
        """Get full task details for the detail panel.

        Args:
            task_id: ID of the task to get details for.

        Returns:
            Task dictionary with acceptance_criteria_details, research,
            implementation_notes, testing_steps, and dependency_details,
            or None if task not found.

        Raises:
            DataFetchError: If task details cannot be fetched from the service.
        """

        def _sync_get() -> dict[str, Any] | None:
            service = self._get_task_service()
            result = service.get_task(task_id)

            if result.is_failure:
                raise DataFetchError(
                    "fetch task detail",
                    result.error_message or "Unknown error",
                )

            task = result.data
            if task is None:
                return None

            # Resolve dependency titles if dependencies exist
            if task.get("dependencies"):
                task["dependency_details"] = self._resolve_dependency_titles(
                    task["dependencies"], service
                )

            return task

        return await asyncio.to_thread(_sync_get)

    def _resolve_dependency_titles(self, dep_ids: list[str], service: Any) -> list[dict[str, Any]]:
        """Resolve dependency IDs to titles for display.

        Args:
            dep_ids: List of dependency task IDs.
            service: TaskService instance.

        Returns:
            List of dictionaries with id, title, and status for each dependency.
        """
        details: list[dict[str, Any]] = []
        for dep_id in dep_ids:
            result = service.get_task(dep_id)
            if result.is_success and result.data:
                details.append(
                    {
                        "id": dep_id,
                        "title": result.data.get("title", "Unknown"),
                        "status": result.data.get("status", "unknown"),
                    }
                )
            else:
                details.append({"id": dep_id, "title": "Unknown", "status": "unknown"})
        return details

    async def toggle_task_status(self, task_id: str, current_status: str) -> bool:
        """Toggle task status using the status cycle.

        Uses STATUS_CYCLE from constants to determine the next status:
        pending -> in-progress -> done -> pending

        Args:
            task_id: ID of the task to toggle.
            current_status: Current status of the task.

        Returns:
            True if status was updated successfully.

        Raises:
            DataUpdateError: If status cannot be updated.
        """
        next_status = STATUS_CYCLE.get(current_status, "pending")
        return await self.update_task_status(task_id, next_status)

    async def update_task_status(self, task_id: str, status: str) -> bool:
        """Update task status.

        Args:
            task_id: ID of the task to update.
            status: New status value.

        Returns:
            True if status was updated successfully.

        Raises:
            DataUpdateError: If status cannot be updated.
        """

        def _sync_update() -> bool:
            service = self._get_task_service()
            result = service.update_task(task_id, status=status)
            if result.is_failure:
                raise DataUpdateError(
                    "update task status",
                    task_id,
                    result.error_message or "Unknown error",
                )
            return True

        return await asyncio.to_thread(_sync_update)

    async def update_task_priority(self, task_id: str, priority: str) -> bool:
        """Update task priority.

        Args:
            task_id: ID of the task to update.
            priority: New priority value (high/medium/low).

        Returns:
            True if priority was updated successfully.

        Raises:
            DataUpdateError: If priority cannot be updated.
        """

        def _sync_update() -> bool:
            service = self._get_task_service()
            result = service.update_task(task_id, priority=priority)
            if result.is_failure:
                raise DataUpdateError(
                    "update task priority",
                    task_id,
                    result.error_message or "Unknown error",
                )
            return True

        return await asyncio.to_thread(_sync_update)

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task.

        Args:
            task_id: ID of the task to delete.

        Returns:
            True if deletion was successful.

        Raises:
            DataUpdateError: If task cannot be deleted.
        """

        def _sync_delete() -> bool:
            service = self._get_task_service()
            result = service.delete_task(task_id)
            if result.is_failure:
                raise DataUpdateError(
                    "delete task",
                    task_id,
                    result.error_message or "Unknown error",
                )
            return True

        return await asyncio.to_thread(_sync_delete)

    # =========================================================================
    # Acceptance Criteria Operations
    # =========================================================================

    async def toggle_criterion_met(self, criterion_entity_id: str, is_met: bool) -> bool:
        """Toggle acceptance criterion met status.

        Args:
            criterion_entity_id: The memory entity ID (not association ID).
            is_met: New met status.

        Returns:
            True if the update was successful.

        Raises:
            DataUpdateError: If criterion cannot be updated.
        """

        def _sync_toggle() -> bool:
            service = self._get_task_service()
            if is_met:
                result = service.mark_criteria_met(criterion_entity_id)
            else:
                result = service.mark_criteria_unmet(criterion_entity_id)

            if result.is_failure:
                raise DataUpdateError(
                    "toggle criterion",
                    criterion_entity_id,
                    result.error_message or "Update failed",
                )
            return True

        return await asyncio.to_thread(_sync_toggle)

    # =========================================================================
    # Bulk Operations
    # =========================================================================

    async def bulk_delete_tasks(self, task_ids: list[str]) -> bool:
        """Delete multiple tasks in a batch operation.

        Args:
            task_ids: List of task IDs to delete.

        Returns:
            True if all deletions were successful.

        Raises:
            DataUpdateError: If any task cannot be deleted.
        """

        def _sync_bulk_delete() -> bool:
            service = self._get_task_service()
            failed_ids = []

            for task_id in task_ids:
                result = service.delete_task(task_id)
                if result.is_failure:
                    failed_ids.append(task_id)

            if failed_ids:
                raise DataUpdateError(
                    "bulk delete tasks",
                    ", ".join(failed_ids[:3]),  # Show first 3 failed IDs
                    f"Failed to delete {len(failed_ids)} task(s)",
                )
            return True

        return await asyncio.to_thread(_sync_bulk_delete)

    async def bulk_update_task_status(self, task_ids: list[str], status: str) -> bool:
        """Update status for multiple tasks in a batch operation.

        Args:
            task_ids: List of task IDs to update.
            status: New status value.

        Returns:
            True if all updates were successful.

        Raises:
            DataUpdateError: If any task cannot be updated.
        """

        def _sync_bulk_update_status() -> bool:
            service = self._get_task_service()
            failed_ids = []

            for task_id in task_ids:
                result = service.update_task(task_id, status=status)
                if result.is_failure:
                    failed_ids.append(task_id)

            if failed_ids:
                raise DataUpdateError(
                    "bulk update task status",
                    ", ".join(failed_ids[:3]),  # Show first 3 failed IDs
                    f"Failed to update {len(failed_ids)} task(s)",
                )
            return True

        return await asyncio.to_thread(_sync_bulk_update_status)

    async def bulk_update_task_priority(self, task_ids: list[str], priority: str) -> bool:
        """Update priority for multiple tasks in a batch operation.

        Args:
            task_ids: List of task IDs to update.
            priority: New priority value (high/medium/low).

        Returns:
            True if all updates were successful.

        Raises:
            DataUpdateError: If any task cannot be updated.
        """

        def _sync_bulk_update_priority() -> bool:
            service = self._get_task_service()
            failed_ids = []

            for task_id in task_ids:
                result = service.update_task(task_id, priority=priority)
                if result.is_failure:
                    failed_ids.append(task_id)

            if failed_ids:
                raise DataUpdateError(
                    "bulk update task priority",
                    ", ".join(failed_ids[:3]),  # Show first 3 failed IDs
                    f"Failed to update {len(failed_ids)} task(s)",
                )
            return True

        return await asyncio.to_thread(_sync_bulk_update_priority)

    # =========================================================================
    # Task Count Operations (for delete modals)
    # =========================================================================

    async def get_task_counts(self, task_id: str) -> dict[str, int]:
        """Get counts of associated data for a task (for delete confirmation).

        Args:
            task_id: ID of the task.

        Returns:
            Dictionary with counts:
                - research_items: Number of research items
                - acceptance_criteria: Number of acceptance criteria
                - implementation_notes: Number of implementation notes
        """

        def _sync_get() -> dict[str, int]:
            service = self._get_task_service()
            result = service.get_task(task_id)

            if result.is_failure or result.data is None:
                return {
                    "research_items": 0,
                    "acceptance_criteria": 0,
                    "implementation_notes": 0,
                }

            task = result.data
            return {
                "research_items": len(task.get("research", [])),
                "acceptance_criteria": len(task.get("acceptance_criteria_details", [])),
                "implementation_notes": len(task.get("implementation_notes", [])),
            }

        return await asyncio.to_thread(_sync_get)
