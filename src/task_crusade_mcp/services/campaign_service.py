"""
Campaign Service - Business logic for campaign operations.

Provides high-level campaign operations with proper error handling
and orchestration of repository calls.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from task_crusade_mcp.database.repositories import (
    CampaignRepository,
    MemoryAssociationRepository,
    MemoryEntityRepository,
    MemorySessionRepository,
    TaskRepository,
)
from task_crusade_mcp.domain.entities.result_types import (
    DomainError,
    DomainResult,
    DomainSuccess,
)

if TYPE_CHECKING:
    from task_crusade_mcp.services.hint_generator import HintGenerator

logger = logging.getLogger(__name__)


class CampaignService:
    """
    Service for campaign business logic.

    Orchestrates campaign operations including CRUD, progress tracking,
    and campaign-level research management.
    """

    def __init__(
        self,
        campaign_repo: CampaignRepository,
        task_repo: TaskRepository,
        memory_session_repo: MemorySessionRepository,
        memory_entity_repo: MemoryEntityRepository,
        memory_association_repo: MemoryAssociationRepository,
        hint_generator: Optional["HintGenerator"] = None,
    ):
        """Initialize service with repositories and hint generator."""
        self.campaign_repo = campaign_repo
        self.task_repo = task_repo
        self.memory_session_repo = memory_session_repo
        self.memory_entity_repo = memory_entity_repo
        self.memory_association_repo = memory_association_repo
        self._hint_generator = hint_generator

    # --- Helper Methods ---

    def _validate_result_data(
        self,
        result: DomainResult[Any],
        operation: str,
    ) -> DomainResult[Any]:
        """
        Validate that a successful result has data.

        Protects against None dereference when accessing result.data attributes.

        Args:
            result: The result to validate
            operation: Description of the operation for error messages

        Returns:
            The original result if valid, or a DomainError if data is None
        """
        if result.is_failure:
            return result

        if result.data is None:
            return DomainError.operation_failed(
                operation=operation,
                reason="Operation succeeded but returned no data",
                suggestions=["Check database consistency", "Verify repository implementation"],
            )

        return result

    # --- CRUD Operations ---

    def create_campaign(
        self,
        name: str,
        description: Optional[str] = None,
        priority: str = "medium",
        status: str = "planning",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DomainResult[Dict[str, Any]]:
        """
        Create a new campaign.

        Args:
            name: Campaign name (unique).
            description: Campaign description.
            priority: Priority level (low, medium, high, critical).
            status: Initial status (planning, active, paused, completed, cancelled).
            metadata: Additional metadata dictionary.

        Returns:
            DomainResult with created campaign data.
        """
        # Normalize and validate name
        name = name.strip() if name else ""
        if not name:
            return DomainError.validation_error("Campaign name cannot be empty or whitespace")

        result = self.campaign_repo.create_campaign(
            {
                "name": name,
                "description": description or "",
                "priority": priority,
                "status": status,
                "metadata": metadata or {},
            }
        )

        if result.is_success and result.data:
            campaign_data = result.data.to_dict()

            # Generate hints if hint generator is available
            if self._hint_generator:
                hints = self._hint_generator.post_campaign_create(
                    campaign_id=campaign_data["id"],
                    campaign_name=campaign_data["name"],
                )
                hint_data = self._hint_generator.format_for_response(hints)
                campaign_data.update(hint_data)

            return DomainSuccess.create(data=campaign_data)
        return result

    def get_campaign(self, campaign_id: str) -> DomainResult[Dict[str, Any]]:
        """Get campaign by ID."""
        result = self.campaign_repo.get(campaign_id)
        if result.is_success and result.data:
            return DomainSuccess.create(data=result.data.to_dict())
        return result

    def list_campaigns(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> DomainResult[List[Dict[str, Any]]]:
        """List campaigns with optional filtering."""
        filters = {}
        if status:
            filters["status"] = status
        if priority:
            filters["priority"] = priority

        return self.campaign_repo.list(filters=filters, limit=limit, offset=offset)

    def update_campaign(self, campaign_id: str, **updates: Any) -> DomainResult[Dict[str, Any]]:
        """Update a campaign."""
        result = self.campaign_repo.update(campaign_id, updates)
        if result.is_success and result.data:
            return DomainSuccess.create(data=result.data.to_dict())
        return result

    def delete_campaign(self, campaign_id: str) -> DomainResult[Dict[str, Any]]:
        """Delete a campaign and all its tasks."""
        return self.campaign_repo.delete(campaign_id)

    # --- Progress & State Operations ---

    def get_progress_summary(self, campaign_id: str) -> DomainResult[Dict[str, Any]]:
        """Get lightweight progress summary for a campaign."""
        result = self.campaign_repo.get_progress_summary(campaign_id)

        if result.is_success and result.data and self._hint_generator:
            progress_data = result.data
            hints = self._hint_generator.post_campaign_progress(
                campaign_id=campaign_id,
                progress_data=progress_data,
            )
            hint_data = self._hint_generator.format_for_response(hints)
            progress_data.update(hint_data)
            return DomainSuccess.create(data=progress_data)

        return result

    def get_campaign_with_tasks(
        self, campaign_id: str, include_task_details: bool = True
    ) -> DomainResult[Dict[str, Any]]:
        """Get campaign with associated tasks."""
        return self.campaign_repo.get_campaign_with_tasks(campaign_id, include_task_details)

    def get_next_actionable_task(
        self, campaign_id: str, context_depth: str = "basic"
    ) -> DomainResult[Dict[str, Any]]:
        """
        Get the next actionable task for a campaign.

        Args:
            campaign_id: Campaign UUID.
            context_depth: 'basic' or 'full' context level.

        Returns:
            DomainResult with task data including acceptance criteria.
        """
        # Verify campaign exists
        campaign_result = self.campaign_repo.get(campaign_id)
        if campaign_result.is_failure:
            return campaign_result

        # Get next actionable task
        result = self.task_repo.get_next_actionable_task(campaign_id)
        if result.is_failure:
            return result

        task_dto = result.data
        if task_dto is None:
            # Get progress for hints even when no task found
            progress_result = self.campaign_repo.get_progress_summary(campaign_id)
            progress_data = progress_result.data if progress_result.is_success else None

            response_data: Dict[str, Any] = {
                "task": None,
                "campaign_progress": progress_data,
                "message": "No actionable tasks found. All tasks may be blocked or completed.",
            }

            # Generate hints for no actionable task scenario
            if self._hint_generator:
                hints = self._hint_generator.actionable_task_hints(
                    task_data=None,
                    campaign_id=campaign_id,
                    campaign_progress=progress_data,
                    no_actionable=True,
                )
                hint_data = self._hint_generator.format_for_response(hints)
                response_data.update(hint_data)

            return DomainSuccess.create(data=response_data)

        # Get task details
        task_data = task_dto.to_dict()

        # Get acceptance criteria for the task
        criteria_result = self._get_task_criteria(task_dto.id)
        if criteria_result.is_success:
            task_data["acceptance_criteria_details"] = criteria_result.data

        # Include research and notes if full context requested
        if context_depth == "full":
            research_result = self._get_task_research(task_dto.id)
            if research_result.is_success:
                task_data["research"] = research_result.data

            notes_result = self._get_task_notes(task_dto.id)
            if notes_result.is_success:
                task_data["implementation_notes"] = notes_result.data

        # Get campaign progress
        progress_result = self.campaign_repo.get_progress_summary(campaign_id)
        progress_data = progress_result.data if progress_result.is_success else None

        response_data: Dict[str, Any] = {
            "task": task_data,
            "dependencies_met": True,
            "campaign_progress": progress_data,
            "context_depth": context_depth,
        }

        # Generate hints for found actionable task
        if self._hint_generator:
            hints = self._hint_generator.actionable_task_hints(
                task_data=task_data,
                campaign_id=campaign_id,
                campaign_progress=progress_data,
                no_actionable=False,
            )
            hint_data = self._hint_generator.format_for_response(hints)
            response_data.update(hint_data)

        return DomainSuccess.create(data=response_data)

    def get_all_actionable_tasks(
        self, campaign_id: str, max_results: int = 10, context_depth: str = "basic"
    ) -> DomainResult[Dict[str, Any]]:
        """
        Get all actionable tasks for parallel execution.

        Args:
            campaign_id: Campaign UUID.
            max_results: Maximum number of tasks to return.
            context_depth: 'basic' or 'full' context level.

        Returns:
            DomainResult with list of actionable tasks.
        """
        # Verify campaign exists
        campaign_result = self.campaign_repo.get(campaign_id)
        if campaign_result.is_failure:
            return campaign_result

        # Get actionable tasks
        result = self.task_repo.get_actionable_tasks(campaign_id, max_results)
        if result.is_failure:
            return result

        tasks = result.data or []

        # Enrich tasks with criteria
        enriched_tasks = []
        for task_dto in tasks:
            task_data = task_dto.to_dict()

            # Get acceptance criteria
            criteria_result = self._get_task_criteria(task_dto.id)
            if criteria_result.is_success:
                task_data["acceptance_criteria_details"] = criteria_result.data

            if context_depth == "full":
                research_result = self._get_task_research(task_dto.id)
                if research_result.is_success:
                    task_data["research"] = research_result.data

                notes_result = self._get_task_notes(task_dto.id)
                if notes_result.is_success:
                    task_data["implementation_notes"] = notes_result.data

            enriched_tasks.append(task_data)

        # Check for in-progress tasks
        in_progress_tasks = [t for t in tasks if t.status == "in-progress"]
        has_in_progress = len(in_progress_tasks) > 0

        # Get progress summary
        progress_result = self.campaign_repo.get_progress_summary(campaign_id)

        return DomainSuccess.create(
            data={
                "actionable_tasks": enriched_tasks,
                "total_actionable": len(tasks),
                "has_in_progress_tasks": has_in_progress,
                "warnings": (
                    [f"{len(in_progress_tasks)} tasks currently in-progress"]
                    if has_in_progress
                    else []
                ),
                "campaign_progress": progress_result.data if progress_result.is_success else None,
                "context_depth": context_depth,
            }
        )

    # --- Campaign Research Operations (using memory internally) ---

    def add_campaign_research(
        self,
        campaign_id: str,
        content: str,
        research_type: str = "analysis",
    ) -> DomainResult[Dict[str, Any]]:
        """
        Add a research item to a campaign.

        Args:
            campaign_id: Campaign UUID.
            content: Research content.
            research_type: Type of research (strategy, analysis, requirements).

        Returns:
            DomainResult with created research item data.
        """
        # Verify campaign exists
        campaign_result = self.campaign_repo.get(campaign_id)
        if campaign_result.is_failure:
            return campaign_result

        # Get or create memory session for campaign research
        session_name = f"campaign-research-{campaign_id}"
        session_result = self.memory_session_repo.get_or_create(
            name=session_name, workflow_type="campaign-research"
        )
        if session_result.is_failure:
            return session_result

        session_id = session_result.data.id

        # Create memory entity for research item
        entity_result = self.memory_entity_repo.create(
            {
                "session_id": session_id,
                "name": f"research-{research_type}",
                "entity_type": "campaign_research",
                "observations": [content],
                "metadata": {"research_type": research_type},
            }
        )
        entity_result = self._validate_result_data(
            entity_result, "create campaign research entity"
        )
        if entity_result.is_failure:
            return entity_result

        entity_id = entity_result.data.id

        # Create association to campaign
        assoc_result = self.memory_association_repo.create(
            {
                "memory_entity_id": entity_id,
                "campaign_id": campaign_id,
                "association_type": "research",
                "notes": research_type,
            }
        )
        if assoc_result.is_failure:
            return assoc_result

        return DomainSuccess.create(
            data={
                "id": entity_id,
                "campaign_id": campaign_id,
                "content": content,
                "research_type": research_type,
            }
        )

    def list_campaign_research(
        self, campaign_id: str, research_type: Optional[str] = None
    ) -> DomainResult[List[Dict[str, Any]]]:
        """
        List research items for a campaign.

        Args:
            campaign_id: Campaign UUID.
            research_type: Optional filter by research type.

        Returns:
            DomainResult with list of research items.
        """
        # Verify campaign exists
        campaign_result = self.campaign_repo.get(campaign_id)
        if campaign_result.is_failure:
            return campaign_result

        # Get associations for campaign
        assoc_result = self.memory_association_repo.list_by_campaign(
            campaign_id, association_type="research"
        )
        if assoc_result.is_failure:
            return assoc_result

        research_items = []
        failed_entities = []
        for assoc in assoc_result.data or []:
            # Get the entity
            entity_result = self.memory_entity_repo.get(assoc.memory_entity_id)
            if entity_result.is_failure:
                failed_entities.append(
                    {"entity_id": assoc.memory_entity_id, "error": entity_result.error_message}
                )
                logger.warning(
                    f"Failed to retrieve research entity {assoc.memory_entity_id} "
                    f"for campaign {campaign_id}: {entity_result.error_message}"
                )
                continue

            entity = entity_result.data
            entity_type = entity.metadata.get("research_type", "analysis")

            # Filter by research_type if specified
            if research_type and entity_type != research_type:
                continue

            observations = entity.observations
            content = observations[0] if observations else ""

            research_items.append(
                {
                    "id": entity.id,
                    "content": content,
                    "research_type": entity_type,
                    "order_index": assoc.order_index,
                    "created_at": entity.created_at.isoformat() if entity.created_at else None,
                }
            )

        if failed_entities:
            return DomainSuccess.create(
                data=research_items,
                suggestions=[
                    f"Warning: {len(failed_entities)} research items could not be retrieved",
                    "Some research data may be incomplete or corrupted",
                    "Consider running database integrity check",
                ],
            )

        return DomainSuccess.create(data=research_items)

    # --- Internal helper methods ---

    def _get_task_criteria(self, task_id: str) -> DomainResult[List[Dict[str, Any]]]:
        """Get acceptance criteria for a task."""
        assoc_result = self.memory_association_repo.list_by_task(
            task_id, association_type="acceptance_criteria"
        )
        if assoc_result.is_failure:
            return DomainSuccess.create(data=[])

        criteria = []
        for assoc in assoc_result.data or []:
            entity_result = self.memory_entity_repo.get(assoc.memory_entity_id)
            if entity_result.is_failure:
                continue

            entity = entity_result.data
            observations = entity.observations
            content = observations[0] if observations else ""
            is_met = entity.metadata.get("is_met", False)

            criteria.append(
                {
                    "id": entity.id,
                    "content": content,
                    "is_met": is_met,
                    "order_index": assoc.order_index,
                }
            )

        return DomainSuccess.create(data=criteria)

    def _get_task_research(self, task_id: str) -> DomainResult[List[Dict[str, Any]]]:
        """Get research items for a task."""
        assoc_result = self.memory_association_repo.list_by_task(
            task_id, association_type="research"
        )
        if assoc_result.is_failure:
            return DomainSuccess.create(data=[])

        research = []
        for assoc in assoc_result.data or []:
            entity_result = self.memory_entity_repo.get(assoc.memory_entity_id)
            if entity_result.is_failure:
                continue

            entity = entity_result.data
            observations = entity.observations
            content = observations[0] if observations else ""
            research_type = entity.metadata.get("research_type", "findings")

            research.append(
                {
                    "id": entity.id,
                    "content": content,
                    "type": research_type,
                    "order_index": assoc.order_index,
                }
            )

        return DomainSuccess.create(data=research)

    def _get_task_notes(self, task_id: str) -> DomainResult[List[Dict[str, Any]]]:
        """Get implementation notes for a task."""
        assoc_result = self.memory_association_repo.list_by_task(
            task_id, association_type="implementation_note"
        )
        if assoc_result.is_failure:
            return DomainSuccess.create(data=[])

        notes = []
        for assoc in assoc_result.data or []:
            entity_result = self.memory_entity_repo.get(assoc.memory_entity_id)
            if entity_result.is_failure:
                continue

            entity = entity_result.data
            observations = entity.observations
            content = observations[0] if observations else ""

            notes.append(
                {
                    "id": entity.id,
                    "content": content,
                    "order_index": assoc.order_index,
                }
            )

        return DomainSuccess.create(data=notes)
