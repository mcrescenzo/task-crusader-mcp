"""
Task Service - Business logic for task operations.

Provides high-level task operations with proper error handling
and orchestration of repository calls.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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
    ):
        """Initialize service with repositories."""
        self.task_repo = task_repo
        self.campaign_repo = campaign_repo
        self.memory_session_repo = memory_session_repo
        self.memory_entity_repo = memory_entity_repo
        self.memory_association_repo = memory_association_repo

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
        result = self.task_repo.update(task_id, updates)
        if result.is_failure:
            return result

        return DomainSuccess.create(data=result.data.to_dict())

    def delete_task(self, task_id: str) -> DomainResult[Dict[str, Any]]:
        """Delete a task and its associated memory entities."""
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

        # Update task status
        return self.update_task(
            task_id,
            status="done",
            completed_at=datetime.now(timezone.utc),
        )

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

        return DomainSuccess.create(
            data={
                "id": criteria_id,
                "content": content,
                "is_met": True,
            }
        )

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

        return DomainSuccess.create(
            data={
                "id": criteria_id,
                "content": content,
                "is_met": False,
            }
        )

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
