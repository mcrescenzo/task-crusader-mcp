"""
Task Service - Business logic for task operations.

Provides high-level task operations with proper error handling
and orchestration of repository calls.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
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


class TaskService:
    """
    Service for task business logic.

    Orchestrates task operations including CRUD, acceptance criteria,
    research items, and implementation notes.
    """

    def __init__(
        self,
        task_repo: TaskRepository,
        campaign_repo: CampaignRepository,
        memory_session_repo: MemorySessionRepository,
        memory_entity_repo: MemoryEntityRepository,
        memory_association_repo: MemoryAssociationRepository,
        hint_generator: Optional["HintGenerator"] = None,
    ):
        """Initialize service with repositories and hint generator."""
        self.task_repo = task_repo
        self.campaign_repo = campaign_repo
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

    def create_task(
        self,
        title: str,
        campaign_id: str,
        description: Optional[str] = None,
        priority: str = "medium",
        status: str = "pending",
        category: Optional[str] = None,
        task_type: str = "code",
        dependencies: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        acceptance_criteria: Optional[List[str]] = None,
        research_items: Optional[List[Dict[str, str]]] = None,
    ) -> DomainResult[Dict[str, Any]]:
        """
        Create a new task.

        Args:
            title: Task title.
            campaign_id: Parent campaign UUID.
            description: Task description.
            priority: Priority level (low, medium, high, critical).
            status: Initial status (pending, in-progress, blocked, done, cancelled).
            category: Task category.
            task_type: Task type (code, research, test, documentation, etc.).
            dependencies: List of task IDs this task depends on.
            tags: List of tags.
            acceptance_criteria: Optional list of acceptance criteria strings.
            research_items: Optional list of research item dicts with 'content' and 'type'.

        Returns:
            DomainResult with created task data.
        """
        # Normalize and validate title
        title = title.strip() if title else ""
        if not title:
            return DomainError.validation_error("Task title cannot be empty or whitespace")

        # Verify campaign exists
        campaign_result = self.campaign_repo.get(campaign_id)
        if campaign_result.is_failure:
            return DomainError.not_found("Campaign", campaign_id)

        # Create task
        result = self.task_repo.create(
            {
                "title": title,
                "campaign_id": campaign_id,
                "description": description or "",
                "priority": priority,
                "status": status,
                "category": category,
                "type": task_type,
                "dependencies": dependencies or [],
                "tags": tags or [],
            }
        )

        if result.is_failure:
            return result

        task_dto = result.data
        task_data = task_dto.to_dict()

        # Add acceptance criteria if provided
        if acceptance_criteria:
            criteria_results = []
            for criterion in acceptance_criteria:
                criteria_result = self.add_acceptance_criteria(task_dto.id, criterion)
                if criteria_result.is_success:
                    criteria_results.append(criteria_result.data)
            task_data["acceptance_criteria_details"] = criteria_results

        # Add research items if provided
        if research_items:
            research_results = []
            for item in research_items:
                content = item.get("content", "")
                research_type = item.get("type", "findings")
                research_result = self.add_research(task_dto.id, content, research_type)
                if research_result.is_success:
                    research_results.append(research_result.data)
            task_data["research"] = research_results

        # Generate hints if hint generator is available
        if self._hint_generator:
            criteria_details = task_data.get("acceptance_criteria_details", [])
            has_criteria = len(criteria_details) > 0
            hints = self._hint_generator.post_task_create(
                task_id=task_dto.id,
                task_title=task_dto.title,
                campaign_id=campaign_id,
                has_acceptance_criteria=has_criteria,
                criteria_count=len(criteria_details),
            )
            hint_data = self._hint_generator.format_for_response(hints)
            task_data.update(hint_data)

        return DomainSuccess.create(data=task_data)

    def get_task(self, task_id: str) -> DomainResult[Dict[str, Any]]:
        """
        Get task by ID with full details.

        Returns task data including acceptance criteria, research, and notes.
        """
        result = self.task_repo.get(task_id)
        if result.is_failure:
            return result

        task_data = result.data.to_dict()

        # Get acceptance criteria
        criteria = self._get_task_criteria(task_id)
        task_data["acceptance_criteria_details"] = criteria

        # Get research
        research = self._get_task_research(task_id)
        task_data["research"] = research

        # Get implementation notes
        notes = self._get_task_notes(task_id)
        task_data["implementation_notes"] = notes

        # Get testing steps
        testing_steps = self._get_task_testing_steps(task_id)
        task_data["testing_steps"] = testing_steps

        return DomainSuccess.create(data=task_data)

    def list_tasks(
        self,
        campaign_id: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> DomainResult[List[Dict[str, Any]]]:
        """List tasks with optional filtering."""
        filters = {}
        if campaign_id:
            filters["campaign_id"] = campaign_id
        if status:
            filters["status"] = status
        if priority:
            filters["priority"] = priority

        result = self.task_repo.list(filters=filters, limit=limit, offset=offset)
        if result.is_failure:
            return result

        return DomainSuccess.create(data=[t.to_dict() for t in result.data or []])

    def update_task(self, task_id: str, **updates: Any) -> DomainResult[Dict[str, Any]]:
        """Update a task."""
        # Get old task state for status change detection
        old_task_result = self.task_repo.get(task_id)
        old_status = None
        if old_task_result.is_success and old_task_result.data:
            old_status = old_task_result.data.status

        result = self.task_repo.update(task_id, updates)
        if result.is_failure:
            return result

        task_data = result.data.to_dict()
        new_status = task_data.get("status")

        # Generate hints for status changes
        if self._hint_generator and old_status and new_status and old_status != new_status:
            # Get criteria counts for the hint
            criteria = self._get_task_criteria(task_id)
            criteria_count = len(criteria)
            unmet_count = len([c for c in criteria if not c.get("is_met", False)])

            hints = self._hint_generator.post_task_status_change(
                task_id=task_id,
                task_title=task_data.get("title", ""),
                campaign_id=task_data.get("campaign_id", ""),
                old_status=old_status,
                new_status=new_status,
                criteria_count=criteria_count,
                unmet_criteria_count=unmet_count,
            )
            hint_data = self._hint_generator.format_for_response(hints)
            task_data.update(hint_data)

        return DomainSuccess.create(data=task_data)

    def delete_task(self, task_id: str) -> DomainResult[Dict[str, Any]]:
        """Delete a task and its associated memory entities."""
        # First, get all memory associations for this task
        assoc_result = self.memory_association_repo.list_by_task(task_id)
        if assoc_result.is_success and assoc_result.data:
            # Delete each memory entity (cascades to delete association)
            for assoc in assoc_result.data:
                self.memory_entity_repo.delete(assoc.memory_entity_id)

        # Now safe to delete the task
        return self.task_repo.delete(task_id)

    def complete_task(self, task_id: str) -> DomainResult[Dict[str, Any]]:
        """
        Mark a task as complete.

        Validates that all acceptance criteria are met before completing.
        """
        # Get task
        result = self.task_repo.get(task_id)
        if result.is_failure:
            return result

        task_dto = result.data
        task_title = task_dto.title
        campaign_id = task_dto.campaign_id

        # Get acceptance criteria
        criteria = self._get_task_criteria(task_id)

        # Check if all criteria are met
        unmet_criteria = [c for c in criteria if not c.get("is_met", False)]
        if unmet_criteria:
            return DomainError.business_rule_violation(
                rule="all_criteria_must_be_met",
                message=f"Cannot complete task: {len(unmet_criteria)} acceptance criteria not met",
                details={"unmet_criteria": unmet_criteria},
                suggestions=["Mark all acceptance criteria as met before completing the task"],
            )

        # Update task status (don't use self.update_task to avoid double hints)
        update_result = self.task_repo.update(
            task_id,
            {"status": "done", "completed_at": datetime.now(timezone.utc)},
        )
        if update_result.is_failure:
            return update_result

        task_data = update_result.data.to_dict()

        # Generate completion hints
        if self._hint_generator:
            # Get campaign progress for context
            progress_result = self.campaign_repo.get_progress_summary(campaign_id)
            progress_data = progress_result.data if progress_result.is_success else None

            hints = self._hint_generator.post_task_complete(
                task_id=task_id,
                task_title=task_title,
                campaign_id=campaign_id,
                campaign_progress=progress_data,
            )
            hint_data = self._hint_generator.format_for_response(hints)
            task_data.update(hint_data)

        return DomainSuccess.create(data=task_data)

    # --- Acceptance Criteria Operations ---

    def add_acceptance_criteria(self, task_id: str, content: str) -> DomainResult[Dict[str, Any]]:
        """
        Add an acceptance criterion to a task.

        Args:
            task_id: Task UUID.
            content: Criterion content.

        Returns:
            DomainResult with created criterion data.
        """
        # Verify task exists
        task_result = self.task_repo.get(task_id)
        if task_result.is_failure:
            return task_result

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
        entity_result = self._validate_result_data(
            entity_result, f"create acceptance criteria entity for task {task_id}"
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

    def mark_criteria_met(self, criteria_id: str) -> DomainResult[Dict[str, Any]]:
        """Mark an acceptance criterion as met."""
        # Get entity
        entity_result = self.memory_entity_repo.get(criteria_id)
        if entity_result.is_failure:
            return entity_result

        entity = entity_result.data
        metadata = entity.metadata or {}
        metadata["is_met"] = True

        # Update entity
        update_result = self.memory_entity_repo.update(criteria_id, {"metadata": metadata})
        if update_result.is_failure:
            return update_result

        observations = entity.observations
        content = observations[0] if observations else ""

        result_data: Dict[str, Any] = {
            "id": criteria_id,
            "content": content,
            "is_met": True,
        }

        # Generate hints if hint generator is available
        if self._hint_generator:
            # Get task info from association
            assoc_result = self.memory_association_repo.get_by_entity(criteria_id)
            if assoc_result.is_success and assoc_result.data:
                task_id = assoc_result.data.task_id
                if task_id:
                    # Get task title
                    task_result = self.task_repo.get(task_id)
                    task_title = (
                        task_result.data.title
                        if task_result.is_success and task_result.data
                        else "Unknown"
                    )

                    # Get criteria counts
                    criteria = self._get_task_criteria(task_id)
                    total_count = len(criteria)
                    met_count = len([c for c in criteria if c.get("is_met", False)])

                    hints = self._hint_generator.post_criteria_met(
                        task_id=task_id,
                        task_title=task_title,
                        criteria_id=criteria_id,
                        met_count=met_count,
                        total_count=total_count,
                    )
                    hint_data = self._hint_generator.format_for_response(hints)
                    result_data.update(hint_data)
                    result_data["task_id"] = task_id

        return DomainSuccess.create(data=result_data)

    def mark_criteria_unmet(self, criteria_id: str) -> DomainResult[Dict[str, Any]]:
        """Mark an acceptance criterion as not met."""
        # Get entity
        entity_result = self.memory_entity_repo.get(criteria_id)
        if entity_result.is_failure:
            return entity_result

        entity = entity_result.data
        metadata = entity.metadata or {}
        metadata["is_met"] = False

        # Update entity
        update_result = self.memory_entity_repo.update(criteria_id, {"metadata": metadata})
        if update_result.is_failure:
            return update_result

        observations = entity.observations
        content = observations[0] if observations else ""

        result_data: Dict[str, Any] = {
            "id": criteria_id,
            "content": content,
            "is_met": False,
        }

        # Generate hints if hint generator is available
        if self._hint_generator:
            # Get task info from association
            assoc_result = self.memory_association_repo.get_by_entity(criteria_id)
            if assoc_result.is_success and assoc_result.data:
                task_id = assoc_result.data.task_id
                if task_id:
                    # Get task title
                    task_result = self.task_repo.get(task_id)
                    task_title = (
                        task_result.data.title
                        if task_result.is_success and task_result.data
                        else "Unknown"
                    )

                    # Get criteria counts
                    criteria = self._get_task_criteria(task_id)
                    total_count = len(criteria)
                    met_count = len([c for c in criteria if c.get("is_met", False)])

                    hints = self._hint_generator.post_criteria_unmet(
                        task_id=task_id,
                        task_title=task_title,
                        criteria_id=criteria_id,
                        met_count=met_count,
                        total_count=total_count,
                    )
                    hint_data = self._hint_generator.format_for_response(hints)
                    result_data.update(hint_data)
                    result_data["task_id"] = task_id

        return DomainSuccess.create(data=result_data)

    # --- Research Operations ---

    def add_research(
        self, task_id: str, content: str, research_type: str = "findings"
    ) -> DomainResult[Dict[str, Any]]:
        """
        Add a research item to a task.

        Args:
            task_id: Task UUID.
            content: Research content.
            research_type: Type of research (findings, approaches, docs).

        Returns:
            DomainResult with created research item data.
        """
        # Verify task exists
        task_result = self.task_repo.get(task_id)
        if task_result.is_failure:
            return task_result

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
        entity_result = self._validate_result_data(
            entity_result, f"create research entity for task {task_id}"
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

    # --- Implementation Notes Operations ---

    def add_implementation_note(self, task_id: str, content: str) -> DomainResult[Dict[str, Any]]:
        """
        Add an implementation note to a task.

        Args:
            task_id: Task UUID.
            content: Note content.

        Returns:
            DomainResult with created note data.
        """
        # Verify task exists
        task_result = self.task_repo.get(task_id)
        if task_result.is_failure:
            return task_result

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
                "name": f"note-{task_id}",
                "entity_type": "implementation_note",
                "observations": [content],
                "metadata": {},
            }
        )
        entity_result = self._validate_result_data(
            entity_result, f"create implementation note entity for task {task_id}"
        )
        if entity_result.is_failure:
            return entity_result

        entity_id = entity_result.data.id

        # Create association to task
        assoc_result = self.memory_association_repo.create(
            {
                "memory_entity_id": entity_id,
                "task_id": task_id,
                "association_type": "implementation_note",
            }
        )
        if assoc_result.is_failure:
            return assoc_result

        return DomainSuccess.create(
            data={
                "id": entity_id,
                "task_id": task_id,
                "content": content,
                "order_index": assoc_result.data.order_index,
            }
        )

    # --- Testing Steps Operations ---

    def add_testing_step(
        self, task_id: str, content: str, step_type: str = "verify"
    ) -> DomainResult[Dict[str, Any]]:
        """
        Add a testing step to a task.

        Args:
            task_id: Task UUID.
            content: Step content.
            step_type: Type of step (setup, trigger, verify, cleanup, debug, fix, iterate).

        Returns:
            DomainResult with created testing step data.
        """
        # Verify task exists
        task_result = self.task_repo.get(task_id)
        if task_result.is_failure:
            return task_result

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
                "name": f"testing-step-{task_id}",
                "entity_type": "testing_step",
                "observations": [content],
                "metadata": {"step_type": step_type},
            }
        )
        entity_result = self._validate_result_data(
            entity_result, f"create testing step entity for task {task_id}"
        )
        if entity_result.is_failure:
            return entity_result

        entity_id = entity_result.data.id

        # Create association to task
        assoc_result = self.memory_association_repo.create(
            {
                "memory_entity_id": entity_id,
                "task_id": task_id,
                "association_type": "testing_step",
                "notes": step_type,
            }
        )
        if assoc_result.is_failure:
            return assoc_result

        return DomainSuccess.create(
            data={
                "id": entity_id,
                "task_id": task_id,
                "content": content,
                "step_type": step_type,
                "order_index": assoc_result.data.order_index,
            }
        )

    # --- Internal helper methods ---

    def _get_task_criteria(self, task_id: str) -> List[Dict[str, Any]]:
        """Get acceptance criteria for a task."""
        assoc_result = self.memory_association_repo.list_by_task(
            task_id, association_type="acceptance_criteria"
        )
        if assoc_result.is_failure:
            return []

        criteria = []
        for assoc in assoc_result.data or []:
            entity_result = self.memory_entity_repo.get(assoc.memory_entity_id)
            if entity_result.is_failure:
                logger.warning(
                    f"Failed to retrieve acceptance criteria entity {assoc.memory_entity_id} "
                    f"for task {task_id}: {entity_result.error_message}"
                )
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

        return criteria

    def _get_task_research(self, task_id: str) -> List[Dict[str, Any]]:
        """Get research items for a task."""
        assoc_result = self.memory_association_repo.list_by_task(
            task_id, association_type="research"
        )
        if assoc_result.is_failure:
            return []

        research = []
        for assoc in assoc_result.data or []:
            entity_result = self.memory_entity_repo.get(assoc.memory_entity_id)
            if entity_result.is_failure:
                logger.warning(
                    f"Failed to retrieve research entity {assoc.memory_entity_id} "
                    f"for task {task_id}: {entity_result.error_message}"
                )
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

        return research

    def _get_task_notes(self, task_id: str) -> List[Dict[str, Any]]:
        """Get implementation notes for a task."""
        assoc_result = self.memory_association_repo.list_by_task(
            task_id, association_type="implementation_note"
        )
        if assoc_result.is_failure:
            return []

        notes = []
        for assoc in assoc_result.data or []:
            entity_result = self.memory_entity_repo.get(assoc.memory_entity_id)
            if entity_result.is_failure:
                logger.warning(
                    f"Failed to retrieve implementation note entity {assoc.memory_entity_id} "
                    f"for task {task_id}: {entity_result.error_message}"
                )
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

        return notes

    def _get_task_testing_steps(self, task_id: str) -> List[Dict[str, Any]]:
        """Get testing steps for a task."""
        assoc_result = self.memory_association_repo.list_by_task(
            task_id, association_type="testing_step"
        )
        if assoc_result.is_failure:
            return []

        steps = []
        for assoc in assoc_result.data or []:
            entity_result = self.memory_entity_repo.get(assoc.memory_entity_id)
            if entity_result.is_failure:
                logger.warning(
                    f"Failed to retrieve testing step entity {assoc.memory_entity_id} "
                    f"for task {task_id}: {entity_result.error_message}"
                )
                continue

            entity = entity_result.data
            observations = entity.observations
            content = observations[0] if observations else ""
            step_type = entity.metadata.get("step_type", "verify")

            steps.append(
                {
                    "id": entity.id,
                    "content": content,
                    "step_type": step_type,
                    "order_index": assoc.order_index,
                }
            )

        return steps
