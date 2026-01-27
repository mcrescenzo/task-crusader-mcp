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
                suggestions=[
                    "Check database consistency",
                    "Verify repository implementation",
                ],
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
            return DomainError.validation_error(
                "Campaign name cannot be empty or whitespace"
            )

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

    def update_campaign(
        self, campaign_id: str, **updates: Any
    ) -> DomainResult[Dict[str, Any]]:
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
        return self.campaign_repo.get_campaign_with_tasks(
            campaign_id, include_task_details
        )

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
                "message": (
                    "No actionable tasks found. "
                    "All tasks may be blocked or completed."
                ),
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
        progress_data = progress_result.data if progress_result.is_success else None

        response_data: Dict[str, Any] = {
            "actionable_tasks": enriched_tasks,
            "total_actionable": len(tasks),
            "has_in_progress_tasks": has_in_progress,
            "warnings": (
                [f"{len(in_progress_tasks)} tasks currently in-progress"]
                if has_in_progress
                else []
            ),
            "campaign_progress": progress_data,
            "context_depth": context_depth,
        }

        # Generate hints for parallel execution
        if self._hint_generator:
            hints = self._hint_generator.actionable_tasks_hints(
                tasks=enriched_tasks,
                campaign_id=campaign_id,
                campaign_progress=progress_data,
            )
            hint_data = self._hint_generator.format_for_response(hints)
            response_data.update(hint_data)

        return DomainSuccess.create(data=response_data)

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

        result_data: Dict[str, Any] = {
            "id": entity_id,
            "campaign_id": campaign_id,
            "content": content,
            "research_type": research_type,
        }

        # Generate hints if hint generator is available
        if self._hint_generator:
            campaign_name = (
                campaign_result.data.name
                if campaign_result.is_success and campaign_result.data
                else "Unknown"
            )
            # Get task count for context
            progress_result = self.campaign_repo.get_progress_summary(campaign_id)
            task_count = 0
            if progress_result.is_success and progress_result.data:
                task_count = progress_result.data.get("total_tasks", 0)

            hints = self._hint_generator.post_campaign_research_add(
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                research_type=research_type,
                task_count=task_count,
            )
            hint_data = self._hint_generator.format_for_response(hints)
            result_data.update(hint_data)

        return DomainSuccess.create(data=result_data)

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
                failed_entities.append({
                    "entity_id": assoc.memory_entity_id,
                    "error": entity_result.error_message,
                })
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

            created_at = (
                entity.created_at.isoformat() if entity.created_at else None
            )
            research_items.append({
                "id": entity.id,
                "content": content,
                "research_type": entity_type,
                "order_index": assoc.order_index,
                "created_at": created_at,
            })

        if failed_entities:
            warning_msg = (
                f"Warning: {len(failed_entities)} research items "
                "could not be retrieved"
            )
            return DomainSuccess.create(
                data=research_items,
                suggestions=[
                    warning_msg,
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

    # --- Bulk Operations ---

    def create_campaign_with_tasks(
        self,
        campaign_spec: "CampaignSpec",
    ) -> DomainResult[Dict[str, Any]]:
        """
        Create a campaign with all tasks in a single atomic operation.

        This method creates a campaign and all its tasks, including their
        acceptance criteria and research items, within a single transaction.
        If any operation fails, the entire transaction is rolled back.

        Args:
            campaign_spec: CampaignSpec containing campaign and tasks data.

        Returns:
            DomainResult containing:
            - campaign: Created campaign data
            - tasks: List of created tasks with temp_id included
            - temp_id_to_uuid: Mapping of temp_ids to actual UUIDs
            - summary: Creation summary statistics
        """
        from task_crusade_mcp.domain.entities.campaign_spec import CampaignSpec
        from task_crusade_mcp.services.dependency_validator import DependencyValidator

        # Step 1: Validate the dependency graph
        validator = DependencyValidator(campaign_spec.tasks)
        validation_result = validator.validate()

        if validation_result.is_failure:
            return validation_result

        topological_order = validation_result.data

        # Step 2: Create the campaign
        campaign_result = self.campaign_repo.create_campaign(
            {
                "name": campaign_spec.name,
                "description": campaign_spec.description or "",
                "priority": campaign_spec.priority,
                "status": campaign_spec.status,
                "metadata": campaign_spec.metadata,
            }
        )

        if campaign_result.is_failure:
            return campaign_result

        campaign_dto = campaign_result.data
        campaign_id = campaign_dto.id
        campaign_data = campaign_dto.to_dict()

        # Step 3: Add campaign research if provided
        for research in campaign_spec.research:
            self.add_campaign_research(
                campaign_id=campaign_id,
                content=research.content,
                research_type=research.research_type,
            )

        # Step 4: Create tasks in topological order
        temp_id_to_uuid: Dict[str, str] = {}
        created_tasks: List[Dict[str, Any]] = []
        tasks_with_criteria = 0
        tasks_with_research = 0

        for temp_id in topological_order:
            task_spec = campaign_spec.get_task_by_temp_id(temp_id)
            if not task_spec:
                continue

            # Map dependency temp_ids to actual UUIDs
            resolved_dependencies = [
                temp_id_to_uuid[dep_id]
                for dep_id in task_spec.dependencies
                if dep_id in temp_id_to_uuid
            ]

            # Create the task
            task_result = self.task_repo.create(
                {
                    "title": task_spec.title,
                    "campaign_id": campaign_id,
                    "description": task_spec.description or "",
                    "priority": task_spec.priority,
                    "status": task_spec.status,
                    "type": task_spec.task_type,
                    "category": task_spec.category,
                    "tags": task_spec.tags,
                    "dependencies": resolved_dependencies,
                }
            )

            if task_result.is_failure:
                # Rollback: delete the campaign (cascades to tasks)
                self.campaign_repo.delete(campaign_id)
                return DomainError.operation_failed(
                    operation="create_task",
                    reason=f"Failed to create task '{task_spec.title}': {task_result.error_message}",
                )

            task_dto = task_result.data
            task_id = task_dto.id
            temp_id_to_uuid[temp_id] = task_id

            task_data = task_dto.to_dict()
            task_data["temp_id"] = temp_id

            # Add acceptance criteria
            if task_spec.acceptance_criteria:
                tasks_with_criteria += 1
                criteria_details = []
                for criterion in task_spec.acceptance_criteria:
                    criteria_result = self._add_task_criteria(task_id, criterion)
                    if criteria_result.is_success:
                        criteria_details.append(criteria_result.data)
                task_data["acceptance_criteria_details"] = criteria_details

            # Add research items
            if task_spec.research:
                tasks_with_research += 1
                research_details = []
                for research in task_spec.research:
                    research_result = self._add_task_research(
                        task_id, research.content, research.research_type
                    )
                    if research_result.is_success:
                        research_details.append(research_result.data)
                task_data["research"] = research_details

            created_tasks.append(task_data)

        # Build response
        result_data: Dict[str, Any] = {
            "campaign": campaign_data,
            "tasks": created_tasks,
            "temp_id_to_uuid": temp_id_to_uuid,
            "summary": {
                "total_tasks": len(created_tasks),
                "with_criteria": tasks_with_criteria,
                "with_research": tasks_with_research,
            },
        }

        # Generate hints if hint generator is available
        if self._hint_generator:
            hints = self._hint_generator.post_campaign_create_with_tasks(
                campaign_id=campaign_id,
                campaign_name=campaign_spec.name,
                task_count=len(created_tasks),
                tasks_with_criteria=tasks_with_criteria,
            )
            hint_data = self._hint_generator.format_for_response(hints)
            result_data.update(hint_data)

        return DomainSuccess.create(data=result_data)

    def _add_task_criteria(self, task_id: str, content: str) -> DomainResult[Dict[str, Any]]:
        """Add acceptance criterion to a task (internal helper)."""
        # Get or create memory session for task
        session_name = f"task-details-{task_id}"
        session_result = self.memory_session_repo.get_or_create(
            name=session_name, workflow_type="task-details"
        )
        if session_result.is_failure:
            return session_result

        session_id = session_result.data.id

        # Create memory entity for criterion
        entity_result = self.memory_entity_repo.create(
            {
                "session_id": session_id,
                "name": f"criterion-{task_id}",
                "entity_type": "acceptance_criteria",
                "observations": [content],
                "metadata": {"is_met": False},
            }
        )
        if entity_result.is_failure:
            return entity_result

        entity_id = entity_result.data.id

        # Create association to task
        assoc_result = self.memory_association_repo.create(
            {
                "memory_entity_id": entity_id,
                "task_id": task_id,
                "association_type": "acceptance_criteria",
            }
        )
        if assoc_result.is_failure:
            return assoc_result

        return DomainSuccess.create(
            data={
                "id": entity_id,
                "task_id": task_id,
                "content": content,
                "is_met": False,
                "order_index": assoc_result.data.order_index,
            }
        )

    def _add_task_research(
        self, task_id: str, content: str, research_type: str = "findings"
    ) -> DomainResult[Dict[str, Any]]:
        """Add research item to a task (internal helper)."""
        # Get or create memory session for task
        session_name = f"task-details-{task_id}"
        session_result = self.memory_session_repo.get_or_create(
            name=session_name, workflow_type="task-details"
        )
        if session_result.is_failure:
            return session_result

        session_id = session_result.data.id

        # Create memory entity
        entity_result = self.memory_entity_repo.create(
            {
                "session_id": session_id,
                "name": f"research-{research_type}-{task_id}",
                "entity_type": "research_item",
                "observations": [content],
                "metadata": {"research_type": research_type},
            }
        )
        if entity_result.is_failure:
            return entity_result

        entity_id = entity_result.data.id

        # Create association to task
        assoc_result = self.memory_association_repo.create(
            {
                "memory_entity_id": entity_id,
                "task_id": task_id,
                "association_type": "research",
                "notes": research_type,
            }
        )
        if assoc_result.is_failure:
            return assoc_result

        return DomainSuccess.create(
            data={
                "id": entity_id,
                "task_id": task_id,
                "content": content,
                "type": research_type,
                "order_index": assoc_result.data.order_index,
            }
        )

    # --- Campaign Overview & State Operations ---

    def get_campaign_overview(
        self, campaign_id: str
    ) -> DomainResult[Dict[str, Any]]:
        """
        Get comprehensive campaign overview including progress, recent activity,
        and actionable tasks.

        Args:
            campaign_id: Campaign UUID.

        Returns:
            DomainResult with overview data including progress, recent tasks,
            and next actions.
        """
        # Verify campaign exists
        campaign_result = self.campaign_repo.get(campaign_id)
        if campaign_result.is_failure:
            return campaign_result

        campaign_dto = campaign_result.data
        campaign_data = campaign_dto.to_dict()

        # Get progress summary
        progress_result = self.campaign_repo.get_progress_summary(campaign_id)
        progress_data = progress_result.data if progress_result.is_success else {}

        # Get recent tasks (last 5 modified)
        tasks_result = self.task_repo.list(
            filters={"campaign_id": campaign_id},
            limit=5,
        )
        recent_tasks = []
        if tasks_result.is_success and tasks_result.data:
            recent_tasks = [t.to_dict() for t in tasks_result.data]

        # Get actionable tasks
        actionable_result = self.task_repo.get_actionable_tasks(campaign_id, 5)
        actionable_tasks = []
        if actionable_result.is_success and actionable_result.data:
            actionable_tasks = [t.to_dict() for t in actionable_result.data]

        # Get campaign research
        research_result = self.list_campaign_research(campaign_id)
        research_items = research_result.data if research_result.is_success else []

        result_data: Dict[str, Any] = {
            "campaign": campaign_data,
            "progress": progress_data,
            "recent_tasks": recent_tasks,
            "actionable_tasks": actionable_tasks,
            "research_items": research_items,
            "summary": {
                "total_tasks": progress_data.get("total_tasks", 0),
                "completed_tasks": progress_data.get("tasks_done", 0),
                "in_progress_tasks": progress_data.get("tasks_in_progress", 0),
                "blocked_tasks": progress_data.get("tasks_blocked", 0),
                "completion_rate": progress_data.get("completion_rate", 0.0),
                "actionable_count": len(actionable_tasks),
                "research_count": len(research_items),
            },
        }

        return DomainSuccess.create(data=result_data)

    def get_state_snapshot(self, campaign_id: str) -> DomainResult[Dict[str, Any]]:
        """
        Export full campaign state for backup or analysis.

        Args:
            campaign_id: Campaign UUID.

        Returns:
            DomainResult with complete campaign state including all tasks
            and their details.
        """
        # Verify campaign exists
        campaign_result = self.campaign_repo.get(campaign_id)
        if campaign_result.is_failure:
            return campaign_result

        campaign_dto = campaign_result.data
        campaign_data = campaign_dto.to_dict()

        # Get all tasks with full details
        tasks_result = self.task_repo.list(filters={"campaign_id": campaign_id})
        tasks_data = []
        if tasks_result.is_success and tasks_result.data:
            for task_dto in tasks_result.data:
                task_data = task_dto.to_dict()
                task_id = task_dto.id

                # Get acceptance criteria
                criteria_result = self._get_task_criteria(task_id)
                if criteria_result.is_success:
                    task_data["acceptance_criteria_details"] = criteria_result.data

                # Get research
                research_result = self._get_task_research(task_id)
                if research_result.is_success:
                    task_data["research"] = research_result.data

                # Get notes
                notes_result = self._get_task_notes(task_id)
                if notes_result.is_success:
                    task_data["implementation_notes"] = notes_result.data

                tasks_data.append(task_data)

        # Get campaign research
        research_result = self.list_campaign_research(campaign_id)
        campaign_research = research_result.data if research_result.is_success else []

        # Get progress summary
        progress_result = self.campaign_repo.get_progress_summary(campaign_id)
        progress_data = progress_result.data if progress_result.is_success else {}

        result_data: Dict[str, Any] = {
            "campaign": campaign_data,
            "tasks": tasks_data,
            "campaign_research": campaign_research,
            "progress": progress_data,
            "metadata": {
                "total_tasks": len(tasks_data),
                "total_criteria": sum(
                    len(t.get("acceptance_criteria_details", []))
                    for t in tasks_data
                ),
                "total_research": sum(
                    len(t.get("research", [])) for t in tasks_data
                ) + len(campaign_research),
                "total_notes": sum(
                    len(t.get("implementation_notes", [])) for t in tasks_data
                ),
            },
        }

        return DomainSuccess.create(data=result_data)

    def validate_readiness(self, campaign_id: str) -> DomainResult[Dict[str, Any]]:
        """
        Check if campaign is ready to start execution.

        Validates:
        - Campaign has tasks
        - No circular dependencies
        - All task dependencies reference existing tasks
        - At least one task is actionable

        Args:
            campaign_id: Campaign UUID.

        Returns:
            DomainResult with readiness status and any issues found.
        """
        # Verify campaign exists
        campaign_result = self.campaign_repo.get(campaign_id)
        if campaign_result.is_failure:
            return campaign_result

        campaign_dto = campaign_result.data

        issues: List[str] = []
        warnings: List[str] = []

        # Get all tasks
        tasks_result = self.task_repo.list(filters={"campaign_id": campaign_id})
        tasks = tasks_result.data if tasks_result.is_success else []

        if not tasks:
            issues.append("Campaign has no tasks")

        # Build task ID set for validation
        task_ids = {t.id for t in tasks}

        # Check for invalid dependency references
        for task in tasks:
            for dep_id in task.dependencies or []:
                if dep_id not in task_ids:
                    issues.append(
                        f"Task '{task.title}' has invalid dependency: {dep_id}"
                    )

        # Check for circular dependencies using DFS
        has_cycle, cycle_info = self._detect_dependency_cycle(tasks)
        if has_cycle:
            issues.append(f"Circular dependency detected: {cycle_info}")

        # Check for actionable tasks
        actionable_result = self.task_repo.get_actionable_tasks(campaign_id, 1)
        actionable_count = (
            len(actionable_result.data)
            if actionable_result.is_success and actionable_result.data
            else 0
        )

        if actionable_count == 0 and tasks:
            warnings.append("No actionable tasks - all tasks may be blocked")

        # Check for tasks without acceptance criteria
        tasks_without_criteria = 0
        for task in tasks:
            criteria = self._get_task_criteria(task.id)
            if not criteria:
                tasks_without_criteria += 1

        if tasks_without_criteria > 0:
            warnings.append(
                f"{tasks_without_criteria} tasks have no acceptance criteria"
            )

        is_ready = len(issues) == 0
        result_data: Dict[str, Any] = {
            "campaign_id": campaign_id,
            "campaign_name": campaign_dto.name,
            "is_ready": is_ready,
            "issues": issues,
            "warnings": warnings,
            "summary": {
                "total_tasks": len(tasks),
                "actionable_tasks": actionable_count,
                "tasks_without_criteria": tasks_without_criteria,
            },
        }

        return DomainSuccess.create(data=result_data)

    def _detect_dependency_cycle(
        self, tasks: List[Any]
    ) -> tuple[bool, Optional[str]]:
        """Detect circular dependencies using three-color DFS."""
        # Build adjacency list: task_id -> list of dependent task_ids
        task_map = {t.id: t for t in tasks}
        dependencies = {t.id: t.dependencies or [] for t in tasks}

        WHITE, GRAY, BLACK = 0, 1, 2
        color = {t.id: WHITE for t in tasks}
        path: List[str] = []

        def dfs(task_id: str) -> Optional[str]:
            color[task_id] = GRAY
            path.append(task_id)

            for dep_id in dependencies.get(task_id, []):
                if dep_id not in color:
                    continue  # Invalid reference, handled elsewhere

                if color[dep_id] == GRAY:
                    # Found cycle - build cycle string
                    cycle_start = path.index(dep_id)
                    cycle_tasks = path[cycle_start:] + [dep_id]
                    cycle_names = [
                        task_map[tid].title if tid in task_map else tid
                        for tid in cycle_tasks
                    ]
                    return " -> ".join(cycle_names)

                if color[dep_id] == WHITE:
                    result = dfs(dep_id)
                    if result:
                        return result

            path.pop()
            color[task_id] = BLACK
            return None

        for task_id in color:
            if color[task_id] == WHITE:
                result = dfs(task_id)
                if result:
                    return True, result

        return False, None

    # --- Campaign Research CRUD Operations ---

    def get_campaign_research(
        self, campaign_id: str, research_id: str
    ) -> DomainResult[Dict[str, Any]]:
        """
        Get a single campaign research item by ID.

        Args:
            campaign_id: Campaign UUID.
            research_id: Research item UUID.

        Returns:
            DomainResult with research item data.
        """
        # Verify campaign exists
        campaign_result = self.campaign_repo.get(campaign_id)
        if campaign_result.is_failure:
            return campaign_result

        # Get entity
        entity_result = self.memory_entity_repo.get(research_id)
        if entity_result.is_failure:
            return DomainError.not_found("Research item", research_id)

        entity = entity_result.data

        # Verify it's associated with the campaign
        assoc_result = self.memory_association_repo.get_by_entity(research_id)
        if assoc_result.is_failure:
            return DomainError.not_found("Research item", research_id)

        assoc = assoc_result.data
        if assoc.campaign_id != campaign_id:
            return DomainError.not_found("Research item", research_id)

        observations = entity.observations
        content = observations[0] if observations else ""
        research_type = entity.metadata.get("research_type", "analysis")

        result_data: Dict[str, Any] = {
            "id": entity.id,
            "campaign_id": campaign_id,
            "content": content,
            "research_type": research_type,
            "order_index": assoc.order_index,
            "created_at": (
                entity.created_at.isoformat() if entity.created_at else None
            ),
        }

        return DomainSuccess.create(data=result_data)

    def update_campaign_research(
        self,
        campaign_id: str,
        research_id: str,
        content: Optional[str] = None,
        research_type: Optional[str] = None,
    ) -> DomainResult[Dict[str, Any]]:
        """
        Update a campaign research item.

        Args:
            campaign_id: Campaign UUID.
            research_id: Research item UUID.
            content: New content (optional).
            research_type: New research type (optional).

        Returns:
            DomainResult with updated research item data.
        """
        # Get current research item
        current_result = self.get_campaign_research(campaign_id, research_id)
        if current_result.is_failure:
            return current_result

        # Build updates
        updates: Dict[str, Any] = {}

        if content is not None:
            updates["observations"] = [content]

        if research_type is not None:
            entity_result = self.memory_entity_repo.get(research_id)
            if entity_result.is_success:
                metadata = entity_result.data.metadata or {}
                metadata["research_type"] = research_type
                updates["metadata"] = metadata

        if not updates:
            return current_result

        # Update entity
        update_result = self.memory_entity_repo.update(research_id, updates)
        if update_result.is_failure:
            return update_result

        # Return updated data
        return self.get_campaign_research(campaign_id, research_id)

    def delete_campaign_research(
        self, campaign_id: str, research_id: str
    ) -> DomainResult[Dict[str, Any]]:
        """
        Delete a campaign research item.

        Args:
            campaign_id: Campaign UUID.
            research_id: Research item UUID.

        Returns:
            DomainResult with deletion confirmation.
        """
        # Verify research belongs to campaign
        current_result = self.get_campaign_research(campaign_id, research_id)
        if current_result.is_failure:
            return current_result

        # Delete entity (cascades to association)
        delete_result = self.memory_entity_repo.delete(research_id)
        if delete_result.is_failure:
            return delete_result

        return DomainSuccess.create(
            data={
                "deleted": True,
                "research_id": research_id,
                "campaign_id": campaign_id,
            }
        )

    def reorder_campaign_research(
        self, campaign_id: str, research_id: str, new_order: int
    ) -> DomainResult[Dict[str, Any]]:
        """
        Change the order of a campaign research item.

        Args:
            campaign_id: Campaign UUID.
            research_id: Research item UUID.
            new_order: New order index (0-based).

        Returns:
            DomainResult with updated research item data.
        """
        # Verify research belongs to campaign
        current_result = self.get_campaign_research(campaign_id, research_id)
        if current_result.is_failure:
            return current_result

        # Get association
        assoc_result = self.memory_association_repo.get_by_entity(research_id)
        if assoc_result.is_failure:
            return assoc_result

        # Update order_index
        update_result = self.memory_association_repo.update(
            assoc_result.data.id, {"order_index": new_order}
        )
        if update_result.is_failure:
            return update_result

        # Return updated data
        return self.get_campaign_research(campaign_id, research_id)

    # --- Campaign Task Utilities ---

    def renumber_tasks(
        self, campaign_id: str, start_from: int = 1
    ) -> DomainResult[Dict[str, Any]]:
        """
        Renumber all tasks in a campaign sequentially.

        Tasks are numbered based on their dependency order (topological sort).

        Args:
            campaign_id: Campaign UUID.
            start_from: Starting number (default: 1).

        Returns:
            DomainResult with renumbering summary.
        """
        # Verify campaign exists
        campaign_result = self.campaign_repo.get(campaign_id)
        if campaign_result.is_failure:
            return campaign_result

        # Get all tasks
        tasks_result = self.task_repo.list(filters={"campaign_id": campaign_id})
        if tasks_result.is_failure:
            return tasks_result

        tasks = tasks_result.data or []
        if not tasks:
            return DomainSuccess.create(
                data={
                    "campaign_id": campaign_id,
                    "tasks_renumbered": 0,
                    "message": "No tasks to renumber",
                }
            )

        # Get topological order
        ordered_ids = self._get_topological_order(tasks)

        # Renumber tasks
        renumbered = []
        for idx, task_id in enumerate(ordered_ids):
            task_number = start_from + idx
            task = next((t for t in tasks if t.id == task_id), None)
            if task:
                # Update task priority_order with number
                self.task_repo.update(task_id, {"priority_order": task_number})
                renumbered.append({
                    "task_id": task_id,
                    "title": task.title,
                    "number": task_number,
                })

        result_data: Dict[str, Any] = {
            "campaign_id": campaign_id,
            "tasks_renumbered": len(renumbered),
            "tasks": renumbered,
        }

        return DomainSuccess.create(data=result_data)

    def _get_topological_order(self, tasks: List[Any]) -> List[str]:
        """Get topological order of tasks using Kahn's algorithm."""
        # Build adjacency list and in-degree count
        task_ids = {t.id for t in tasks}
        in_degree = {t.id: 0 for t in tasks}
        dependents: Dict[str, List[str]] = {t.id: [] for t in tasks}

        for task in tasks:
            for dep_id in task.dependencies or []:
                if dep_id in task_ids:
                    in_degree[task.id] += 1
                    dependents[dep_id].append(task.id)

        # Start with tasks that have no dependencies
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        result: List[str] = []

        while queue:
            # Sort by title for deterministic ordering
            queue.sort(
                key=lambda tid: next(
                    (t.title for t in tasks if t.id == tid), ""
                )
            )
            current = queue.pop(0)
            result.append(current)

            for dependent in dependents[current]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # Add any remaining tasks (cycle handling)
        for task in tasks:
            if task.id not in result:
                result.append(task.id)

        return result
