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

from task_crusade_mcp.domain.entities.hint import TaskCompletenessInfo

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
                suggestions=[
                    "Check database consistency",
                    "Verify repository implementation",
                ],
            )

        return result

    def _build_task_completeness_info(
        self,
        task_id: str,
        task_title: str,
        task_status: str,
    ) -> TaskCompletenessInfo:
        """
        Build TaskCompletenessInfo for quality hints.

        Fetches task memory data to determine completeness.

        Args:
            task_id: Task UUID
            task_title: Task title
            task_status: Task status

        Returns:
            TaskCompletenessInfo populated with task quality data
        """
        criteria = self._get_task_criteria(task_id)
        testing_steps = self._get_task_testing_steps(task_id)
        research = self._get_task_research(task_id)

        return TaskCompletenessInfo(
            task_id=task_id,
            task_title=task_title,
            task_status=task_status,
            has_acceptance_criteria=len(criteria) > 0,
            criteria_count=len(criteria),
            has_testing_strategy=len(testing_steps) > 0,
            testing_steps_count=len(testing_steps),
            has_research=len(research) > 0,
        )

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

        # Validate dependencies exist
        if dependencies:
            invalid_deps = []
            for dep_id in dependencies:
                dep_result = self.task_repo.get(dep_id)
                if dep_result.is_failure:
                    invalid_deps.append(dep_id)
            if invalid_deps:
                return DomainError.validation_error(f"Invalid dependency task IDs: {invalid_deps}")

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

        Returns task data including acceptance criteria, research, notes,
        and quality hints for task inspection.
        """
        result = self.task_repo.get(task_id)
        if result.is_failure:
            return result

        task_dto = result.data
        task_data = task_dto.to_dict()

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

        # Generate quality hints for task inspection
        if self._hint_generator:
            completeness_info = TaskCompletenessInfo(
                task_id=task_id,
                task_title=task_dto.title,
                task_status=task_dto.status,
                has_acceptance_criteria=len(criteria) > 0,
                criteria_count=len(criteria),
                has_testing_strategy=len(testing_steps) > 0,
                testing_steps_count=len(testing_steps),
                has_research=len(research) > 0,
            )
            hints = self._hint_generator.task_quality_hints(
                completeness_info=completeness_info,
                context="inspection",
            )
            hint_data = self._hint_generator.format_for_response(hints)
            task_data.update(hint_data)

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
        """
        Update a task.

        Supports three modes for dependency management (choose ONE per call):
        - dependencies: REPLACE all dependencies with this list
        - add_dependencies: ADD task IDs to existing dependencies
        - remove_dependencies: REMOVE task IDs from existing dependencies
        """
        # Get old task state for status change detection and dependency operations
        old_task_result = self.task_repo.get(task_id)
        if old_task_result.is_failure:
            return DomainError.not_found("Task", task_id)

        old_task = old_task_result.data
        old_status = old_task.status

        # Handle dependency operation modes
        dependencies = updates.get("dependencies")
        add_dependencies = updates.pop("add_dependencies", None)
        remove_dependencies = updates.pop("remove_dependencies", None)

        # Validate only one dependency operation is provided
        dep_ops = [
            dependencies is not None,
            add_dependencies is not None,
            remove_dependencies is not None,
        ]
        if sum(dep_ops) > 1:
            return DomainError.validation_error(
                "Only one of 'dependencies', 'add_dependencies', or "
                "'remove_dependencies' can be provided per call"
            )

        # Handle add_dependencies: append to existing
        if add_dependencies is not None:
            existing = list(old_task.dependencies or [])
            # Add new deps, avoiding duplicates
            for dep_id in add_dependencies:
                if dep_id not in existing:
                    existing.append(dep_id)
            updates["dependencies"] = existing
            dependencies = existing

        # Handle remove_dependencies: remove from existing
        if remove_dependencies is not None:
            existing = list(old_task.dependencies or [])
            updates["dependencies"] = [d for d in existing if d not in remove_dependencies]
            dependencies = updates["dependencies"]

        # Validate dependencies if being updated
        if dependencies is not None:
            invalid_deps = []
            for dep_id in dependencies:
                # Prevent self-dependency
                if dep_id == task_id:
                    return DomainError.validation_error(f"Task cannot depend on itself: {task_id}")
                dep_result = self.task_repo.get(dep_id)
                if dep_result.is_failure:
                    invalid_deps.append(dep_id)
            if invalid_deps:
                return DomainError.validation_error(f"Invalid dependency task IDs: {invalid_deps}")

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

            # Get blocking task info when status changes to blocked
            blocking_tasks: Optional[List[Dict[str, Any]]] = None
            if new_status == "blocked":
                dependencies = task_data.get("dependencies", [])
                if dependencies:
                    blocking_tasks = []
                    for dep_id in dependencies:
                        dep_result = self.task_repo.get(dep_id)
                        if dep_result.is_success and dep_result.data:
                            dep_data = dep_result.data
                            # Only include non-completed tasks as blockers
                            if dep_data.status != "done":
                                blocking_tasks.append(
                                    {
                                        "id": dep_data.id,
                                        "title": dep_data.title,
                                        "status": dep_data.status,
                                    }
                                )

            hints = self._hint_generator.post_task_status_change(
                task_id=task_id,
                task_title=task_data.get("title", ""),
                campaign_id=task_data.get("campaign_id", ""),
                old_status=old_status,
                new_status=new_status,
                criteria_count=criteria_count,
                unmet_criteria_count=unmet_count,
                blocking_tasks=blocking_tasks,
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

        result_data: Dict[str, Any] = {
            "id": entity_id,
            "task_id": task_id,
            "content": content,
            "is_met": False,
            "order_index": assoc_result.data.order_index,
        }

        # Generate hints if hint generator is available
        if self._hint_generator:
            task_title = (
                task_result.data.title if task_result.is_success and task_result.data else "Unknown"
            )
            criteria_count = len(self._get_task_criteria(task_id))
            hints = self._hint_generator.post_acceptance_criteria_add(
                task_id=task_id,
                task_title=task_title,
                criteria_count=criteria_count,
            )
            hint_data = self._hint_generator.format_for_response(hints)
            result_data.update(hint_data)

        return DomainSuccess.create(data=result_data)

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

        result_data: Dict[str, Any] = {
            "id": entity_id,
            "task_id": task_id,
            "content": content,
            "type": research_type,
            "order_index": assoc_result.data.order_index,
        }

        # Generate hints if hint generator is available
        if self._hint_generator:
            task_title = (
                task_result.data.title if task_result.is_success and task_result.data else "Unknown"
            )
            hints = self._hint_generator.post_research_add(
                task_id=task_id,
                task_title=task_title,
                research_type=research_type,
            )
            hint_data = self._hint_generator.format_for_response(hints)
            result_data.update(hint_data)

        return DomainSuccess.create(data=result_data)

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

        result_data: Dict[str, Any] = {
            "id": entity_id,
            "task_id": task_id,
            "content": content,
            "order_index": assoc_result.data.order_index,
        }

        # Generate hints if hint generator is available
        if self._hint_generator:
            task_title = (
                task_result.data.title if task_result.is_success and task_result.data else "Unknown"
            )
            # Get unmet criteria for the hint
            criteria = self._get_task_criteria(task_id)
            unmet_criteria = [c for c in criteria if not c.get("is_met", False)]

            hints = self._hint_generator.post_implementation_note_add(
                task_id=task_id,
                task_title=task_title,
                unmet_criteria=unmet_criteria,
            )
            hint_data = self._hint_generator.format_for_response(hints)
            result_data.update(hint_data)

        return DomainSuccess.create(data=result_data)

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

        result_data: Dict[str, Any] = {
            "id": entity_id,
            "task_id": task_id,
            "content": content,
            "step_type": step_type,
            "order_index": assoc_result.data.order_index,
        }

        # Generate hints if hint generator is available
        if self._hint_generator:
            task_title = (
                task_result.data.title if task_result.is_success and task_result.data else "Unknown"
            )
            hints = self._hint_generator.post_testing_step_add(
                task_id=task_id,
                task_title=task_title,
                step_type=step_type,
            )
            hint_data = self._hint_generator.format_for_response(hints)
            result_data.update(hint_data)

        return DomainSuccess.create(data=result_data)

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
            test_status = entity.metadata.get("test_status", "pending")

            steps.append(
                {
                    "id": entity.id,
                    "content": content,
                    "step_type": step_type,
                    "test_status": test_status,
                    "order_index": assoc.order_index,
                }
            )

        return steps

    # --- Search & Analytics Operations ---

    def search_tasks(
        self,
        query: str,
        campaign_id: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 50,
    ) -> DomainResult[Dict[str, Any]]:
        """
        Full-text search across task titles and descriptions.

        Args:
            query: Search query string.
            campaign_id: Optional filter by campaign.
            status: Optional filter by status.
            priority: Optional filter by priority.
            limit: Maximum results to return.

        Returns:
            DomainResult with matching tasks.
        """
        query = query.strip().lower() if query else ""
        if not query:
            return DomainError.validation_error("Search query cannot be empty")

        # Build filters
        filters: Dict[str, Any] = {}
        if campaign_id:
            filters["campaign_id"] = campaign_id
        if status:
            filters["status"] = status
        if priority:
            filters["priority"] = priority

        # Get all tasks matching filters
        result = self.task_repo.list(filters=filters, limit=500)  # Get more for search
        if result.is_failure:
            return result

        # Filter by query (case-insensitive search in title and description)
        matching_tasks = []
        for task_dto in result.data or []:
            title_match = query in (task_dto.title or "").lower()
            desc_match = query in (task_dto.description or "").lower()
            if title_match or desc_match:
                task_data = task_dto.to_dict()
                # Add match info
                task_data["_match"] = {
                    "title": title_match,
                    "description": desc_match,
                }
                matching_tasks.append(task_data)

                if len(matching_tasks) >= limit:
                    break

        result_data: Dict[str, Any] = {
            "query": query,
            "total_matches": len(matching_tasks),
            "tasks": matching_tasks,
            "filters_applied": {
                "campaign_id": campaign_id,
                "status": status,
                "priority": priority,
            },
        }

        return DomainSuccess.create(data=result_data)

    def get_task_stats(self, campaign_id: Optional[str] = None) -> DomainResult[Dict[str, Any]]:
        """
        Get aggregate task statistics.

        Args:
            campaign_id: Optional filter by campaign.

        Returns:
            DomainResult with task statistics by status, priority, and type.
        """
        # Build filters
        filters: Dict[str, Any] = {}
        if campaign_id:
            filters["campaign_id"] = campaign_id

        # Get all tasks
        result = self.task_repo.list(filters=filters, limit=1000)
        if result.is_failure:
            return result

        tasks = result.data or []

        # Calculate statistics
        by_status: Dict[str, int] = {}
        by_priority: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        by_campaign: Dict[str, int] = {}
        total_with_criteria = 0
        total_criteria_met = 0
        total_criteria = 0

        for task_dto in tasks:
            # Count by status
            status = task_dto.status or "unknown"
            by_status[status] = by_status.get(status, 0) + 1

            # Count by priority
            priority = task_dto.priority or "medium"
            by_priority[priority] = by_priority.get(priority, 0) + 1

            # Count by type
            task_type = task_dto.type or "code"
            by_type[task_type] = by_type.get(task_type, 0) + 1

            # Count by campaign
            cid = task_dto.campaign_id
            by_campaign[cid] = by_campaign.get(cid, 0) + 1

            # Count criteria
            criteria = self._get_task_criteria(task_dto.id)
            if criteria:
                total_with_criteria += 1
                total_criteria += len(criteria)
                total_criteria_met += len([c for c in criteria if c.get("is_met")])

        # Calculate completion rate
        total = len(tasks)
        completed = by_status.get("done", 0)
        completion_rate = (completed / total * 100) if total > 0 else 0.0

        # Calculate criteria completion rate
        criteria_rate = (total_criteria_met / total_criteria * 100) if total_criteria > 0 else 0.0

        result_data: Dict[str, Any] = {
            "total_tasks": total,
            "completion_rate": round(completion_rate, 1),
            "by_status": by_status,
            "by_priority": by_priority,
            "by_type": by_type,
            "by_campaign": by_campaign if not campaign_id else None,
            "criteria": {
                "tasks_with_criteria": total_with_criteria,
                "total_criteria": total_criteria,
                "criteria_met": total_criteria_met,
                "criteria_completion_rate": round(criteria_rate, 1),
            },
        }

        # Remove None values
        result_data = {k: v for k, v in result_data.items() if v is not None}

        return DomainSuccess.create(data=result_data)

    def get_dependency_info(self, task_id: str) -> DomainResult[Dict[str, Any]]:
        """
        Get upstream dependencies (blockers) and downstream dependents for a task.

        Args:
            task_id: Task UUID.

        Returns:
            DomainResult with dependency information.
        """
        # Verify task exists
        task_result = self.task_repo.get(task_id)
        if task_result.is_failure:
            return task_result

        task_dto = task_result.data

        # Get upstream dependencies (tasks this task depends on)
        upstream: List[Dict[str, Any]] = []
        blocking: List[Dict[str, Any]] = []
        for dep_id in task_dto.dependencies or []:
            dep_result = self.task_repo.get(dep_id)
            if dep_result.is_success and dep_result.data:
                dep_data = dep_result.data
                dep_info = {
                    "id": dep_data.id,
                    "title": dep_data.title,
                    "status": dep_data.status,
                }
                upstream.append(dep_info)
                if dep_data.status != "done":
                    blocking.append(dep_info)

        # Get downstream dependents (tasks that depend on this task)
        campaign_id = task_dto.campaign_id
        all_tasks_result = self.task_repo.list(filters={"campaign_id": campaign_id})
        downstream: List[Dict[str, Any]] = []
        if all_tasks_result.is_success:
            for other_task in all_tasks_result.data or []:
                if task_id in (other_task.dependencies or []):
                    downstream.append(
                        {
                            "id": other_task.id,
                            "title": other_task.title,
                            "status": other_task.status,
                        }
                    )

        is_blocked = len(blocking) > 0
        is_blocking_others = task_dto.status != "done" and len(downstream) > 0

        result_data: Dict[str, Any] = {
            "task": {
                "id": task_dto.id,
                "title": task_dto.title,
                "status": task_dto.status,
            },
            "upstream_dependencies": upstream,
            "downstream_dependents": downstream,
            "blocking_tasks": blocking,
            "summary": {
                "total_upstream": len(upstream),
                "total_downstream": len(downstream),
                "is_blocked": is_blocked,
                "is_blocking_others": is_blocking_others,
                "blocking_count": len(blocking),
            },
        }

        return DomainSuccess.create(data=result_data)

    # --- Bulk & Workflow Operations ---

    def bulk_update_tasks(
        self,
        task_ids: List[str],
        status: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> DomainResult[Dict[str, Any]]:
        """
        Update multiple tasks at once.

        Args:
            task_ids: List of task UUIDs to update.
            status: New status for all tasks.
            priority: New priority for all tasks.

        Returns:
            DomainResult with update summary.
        """
        if not task_ids:
            return DomainError.validation_error("No task IDs provided")

        updates: Dict[str, Any] = {}
        if status:
            updates["status"] = status
        if priority:
            updates["priority"] = priority

        if not updates:
            return DomainError.validation_error("No updates provided")

        updated: List[Dict[str, Any]] = []
        failed: List[Dict[str, Any]] = []

        for task_id in task_ids:
            result = self.task_repo.update(task_id, updates)
            if result.is_success and result.data:
                updated.append(
                    {
                        "id": task_id,
                        "title": result.data.title,
                        "status": result.data.status,
                        "priority": result.data.priority,
                    }
                )
            else:
                failed.append(
                    {
                        "id": task_id,
                        "error": result.error_message or "Update failed",
                    }
                )

        result_data: Dict[str, Any] = {
            "updated_count": len(updated),
            "failed_count": len(failed),
            "updated_tasks": updated,
            "failed_tasks": failed,
            "updates_applied": updates,
        }

        return DomainSuccess.create(data=result_data)

    def create_task_from_template(
        self,
        template_name: str,
        campaign_id: str,
        title: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> DomainResult[Dict[str, Any]]:
        """
        Create a task from a predefined template.

        Args:
            template_name: Name of the template to use.
            campaign_id: Campaign to create the task in.
            title: Override title (optional).
            overrides: Additional field overrides.

        Returns:
            DomainResult with created task.
        """
        # Define templates
        templates: Dict[str, Dict[str, Any]] = {
            "bug-fix": {
                "title": "Bug Fix",
                "description": "Fix reported bug",
                "type": "code",
                "priority": "high",
                "acceptance_criteria": [
                    "Bug is reproducible before fix",
                    "Fix resolves the reported issue",
                    "No regressions introduced",
                    "Tests added for the fix",
                ],
            },
            "feature": {
                "title": "New Feature",
                "description": "Implement new feature",
                "type": "code",
                "priority": "medium",
                "acceptance_criteria": [
                    "Feature implemented per requirements",
                    "Unit tests written",
                    "Documentation updated",
                ],
            },
            "refactor": {
                "title": "Code Refactoring",
                "description": "Refactor code for improved quality",
                "type": "refactor",
                "priority": "low",
                "acceptance_criteria": [
                    "Code refactored successfully",
                    "All existing tests pass",
                    "No functional changes",
                ],
            },
            "research": {
                "title": "Research Task",
                "description": "Research and document findings",
                "type": "research",
                "priority": "medium",
                "acceptance_criteria": [
                    "Research completed",
                    "Findings documented",
                    "Recommendations provided",
                ],
            },
            "test": {
                "title": "Testing Task",
                "description": "Write or improve tests",
                "type": "test",
                "priority": "medium",
                "acceptance_criteria": [
                    "Tests written",
                    "Tests pass",
                    "Coverage improved",
                ],
            },
            "documentation": {
                "title": "Documentation",
                "description": "Write or update documentation",
                "type": "documentation",
                "priority": "low",
                "acceptance_criteria": [
                    "Documentation written",
                    "Documentation reviewed",
                    "Documentation published",
                ],
            },
        }

        template = templates.get(template_name)
        if not template:
            available = ", ".join(templates.keys())
            return DomainError.not_found(
                "Template",
                template_name,
                suggestions=[f"Available templates: {available}"],
            )

        # Build task data from template
        task_data = template.copy()
        criteria = task_data.pop("acceptance_criteria", [])

        # Apply title override
        if title:
            task_data["title"] = title

        # Apply other overrides
        if overrides:
            task_data.update(overrides)

        # Create the task
        return self.create_task(
            title=task_data.get("title", "New Task"),
            campaign_id=campaign_id,
            description=task_data.get("description"),
            priority=task_data.get("priority", "medium"),
            task_type=task_data.get("type", "code"),
            acceptance_criteria=criteria,
        )

    def complete_task_with_workflow(self, task_id: str) -> DomainResult[Dict[str, Any]]:
        """
        Complete a task with full validation.

        Validates:
        - All acceptance criteria are met
        - All dependencies are completed
        - Task is not already completed

        Args:
            task_id: Task UUID.

        Returns:
            DomainResult with completed task or validation errors.
        """
        # Get task
        task_result = self.task_repo.get(task_id)
        if task_result.is_failure:
            return task_result

        task_dto = task_result.data

        # Check if already completed
        if task_dto.status == "done":
            return DomainError.business_rule_violation(
                rule="task_already_completed",
                message="Task is already completed",
            )

        # Check dependencies
        blocking_deps = []
        for dep_id in task_dto.dependencies or []:
            dep_result = self.task_repo.get(dep_id)
            if dep_result.is_success and dep_result.data and dep_result.data.status != "done":
                blocking_deps.append(
                        {
                            "id": dep_id,
                            "title": dep_result.data.title,
                            "status": dep_result.data.status,
                        }
                    )

        if blocking_deps:
            return DomainError.business_rule_violation(
                rule="dependencies_not_met",
                message=f"Cannot complete: {len(blocking_deps)} blocking dependencies",
                details={"blocking_dependencies": blocking_deps},
                suggestions=[
                    (
                        f"Complete task '{blocking_deps[0]['title']}' first"
                        if blocking_deps
                        else "Complete blocking dependencies"
                    )
                ],
            )

        # Check acceptance criteria
        criteria = self._get_task_criteria(task_id)
        unmet_criteria = [c for c in criteria if not c.get("is_met", False)]

        if unmet_criteria:
            return DomainError.business_rule_violation(
                rule="criteria_not_met",
                message=f"Cannot complete: {len(unmet_criteria)} unmet criteria",
                details={"unmet_criteria": unmet_criteria},
                suggestions=[
                    (
                        f"Mark criterion as met: {unmet_criteria[0].get('content', '')[:50]}"
                        if unmet_criteria
                        else "Mark all criteria as met"
                    )
                ],
            )

        # All validations passed - complete the task
        return self.complete_task(task_id)

    # --- Task Research CRUD Operations ---

    def list_task_research(self, task_id: str) -> DomainResult[Dict[str, Any]]:
        """List all research items for a task."""
        task_result = self.task_repo.get(task_id)
        if task_result.is_failure:
            return task_result

        research = self._get_task_research(task_id)
        return DomainSuccess.create(data={"task_id": task_id, "research": research})

    def get_task_research(self, task_id: str, research_id: str) -> DomainResult[Dict[str, Any]]:
        """Get a single research item."""
        task_result = self.task_repo.get(task_id)
        if task_result.is_failure:
            return task_result

        entity_result = self.memory_entity_repo.get(research_id)
        if entity_result.is_failure:
            return DomainError.not_found("Research item", research_id)

        entity = entity_result.data
        observations = entity.observations
        content = observations[0] if observations else ""
        research_type = entity.metadata.get("research_type", "findings")

        return DomainSuccess.create(
            data={
                "id": entity.id,
                "task_id": task_id,
                "content": content,
                "type": research_type,
            }
        )

    def update_task_research(
        self,
        task_id: str,
        research_id: str,
        content: Optional[str] = None,
        research_type: Optional[str] = None,
    ) -> DomainResult[Dict[str, Any]]:
        """Update a research item."""
        current = self.get_task_research(task_id, research_id)
        if current.is_failure:
            return current

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
            return current

        update_result = self.memory_entity_repo.update(research_id, updates)
        if update_result.is_failure:
            return update_result

        return self.get_task_research(task_id, research_id)

    def delete_task_research(self, task_id: str, research_id: str) -> DomainResult[Dict[str, Any]]:
        """Delete a research item."""
        current = self.get_task_research(task_id, research_id)
        if current.is_failure:
            return current

        delete_result = self.memory_entity_repo.delete(research_id)
        if delete_result.is_failure:
            return delete_result

        return DomainSuccess.create(
            data={
                "deleted": True,
                "research_id": research_id,
                "task_id": task_id,
            }
        )

    def reorder_task_research(
        self, task_id: str, research_id: str, new_order: int
    ) -> DomainResult[Dict[str, Any]]:
        """Change research item order."""
        current = self.get_task_research(task_id, research_id)
        if current.is_failure:
            return current

        assoc_result = self.memory_association_repo.get_by_entity(research_id)
        if assoc_result.is_failure:
            return assoc_result

        update_result = self.memory_association_repo.update(
            assoc_result.data.id, {"order_index": new_order}
        )
        if update_result.is_failure:
            return update_result

        return self.get_task_research(task_id, research_id)

    # --- Task Implementation Notes CRUD Operations ---

    def list_implementation_notes(self, task_id: str) -> DomainResult[Dict[str, Any]]:
        """List all implementation notes for a task."""
        task_result = self.task_repo.get(task_id)
        if task_result.is_failure:
            return task_result

        notes = self._get_task_notes(task_id)
        return DomainSuccess.create(data={"task_id": task_id, "notes": notes})

    def get_implementation_note(self, task_id: str, note_id: str) -> DomainResult[Dict[str, Any]]:
        """Get a single implementation note."""
        task_result = self.task_repo.get(task_id)
        if task_result.is_failure:
            return task_result

        entity_result = self.memory_entity_repo.get(note_id)
        if entity_result.is_failure:
            return DomainError.not_found("Implementation note", note_id)

        entity = entity_result.data
        observations = entity.observations
        content = observations[0] if observations else ""

        return DomainSuccess.create(
            data={
                "id": entity.id,
                "task_id": task_id,
                "content": content,
            }
        )

    def update_implementation_note(
        self, task_id: str, note_id: str, content: str
    ) -> DomainResult[Dict[str, Any]]:
        """Update an implementation note."""
        current = self.get_implementation_note(task_id, note_id)
        if current.is_failure:
            return current

        update_result = self.memory_entity_repo.update(note_id, {"observations": [content]})
        if update_result.is_failure:
            return update_result

        return self.get_implementation_note(task_id, note_id)

    def delete_implementation_note(
        self, task_id: str, note_id: str
    ) -> DomainResult[Dict[str, Any]]:
        """Delete an implementation note."""
        current = self.get_implementation_note(task_id, note_id)
        if current.is_failure:
            return current

        delete_result = self.memory_entity_repo.delete(note_id)
        if delete_result.is_failure:
            return delete_result

        return DomainSuccess.create(
            data={
                "deleted": True,
                "note_id": note_id,
                "task_id": task_id,
            }
        )

    def reorder_implementation_notes(
        self, task_id: str, note_id: str, new_order: int
    ) -> DomainResult[Dict[str, Any]]:
        """Change implementation note order."""
        current = self.get_implementation_note(task_id, note_id)
        if current.is_failure:
            return current

        assoc_result = self.memory_association_repo.get_by_entity(note_id)
        if assoc_result.is_failure:
            return assoc_result

        update_result = self.memory_association_repo.update(
            assoc_result.data.id, {"order_index": new_order}
        )
        if update_result.is_failure:
            return update_result

        return self.get_implementation_note(task_id, note_id)

    # --- Task Acceptance Criteria CRUD Operations ---

    def list_acceptance_criteria(self, task_id: str) -> DomainResult[Dict[str, Any]]:
        """List all acceptance criteria for a task."""
        task_result = self.task_repo.get(task_id)
        if task_result.is_failure:
            return task_result

        criteria = self._get_task_criteria(task_id)
        return DomainSuccess.create(
            data={
                "task_id": task_id,
                "criteria": criteria,
            }
        )

    def get_acceptance_criterion(
        self, task_id: str, criterion_id: str
    ) -> DomainResult[Dict[str, Any]]:
        """Get a single acceptance criterion."""
        task_result = self.task_repo.get(task_id)
        if task_result.is_failure:
            return task_result

        entity_result = self.memory_entity_repo.get(criterion_id)
        if entity_result.is_failure:
            return DomainError.not_found("Acceptance criterion", criterion_id)

        entity = entity_result.data
        observations = entity.observations
        content = observations[0] if observations else ""
        is_met = entity.metadata.get("is_met", False)

        return DomainSuccess.create(
            data={
                "id": entity.id,
                "task_id": task_id,
                "content": content,
                "is_met": is_met,
            }
        )

    def update_acceptance_criterion(
        self, task_id: str, criterion_id: str, content: str
    ) -> DomainResult[Dict[str, Any]]:
        """Update an acceptance criterion description."""
        current = self.get_acceptance_criterion(task_id, criterion_id)
        if current.is_failure:
            return current

        update_result = self.memory_entity_repo.update(criterion_id, {"observations": [content]})
        if update_result.is_failure:
            return update_result

        return self.get_acceptance_criterion(task_id, criterion_id)

    def delete_acceptance_criterion(
        self, task_id: str, criterion_id: str
    ) -> DomainResult[Dict[str, Any]]:
        """Delete an acceptance criterion."""
        current = self.get_acceptance_criterion(task_id, criterion_id)
        if current.is_failure:
            return current

        delete_result = self.memory_entity_repo.delete(criterion_id)
        if delete_result.is_failure:
            return delete_result

        return DomainSuccess.create(
            data={
                "deleted": True,
                "criterion_id": criterion_id,
                "task_id": task_id,
            }
        )

    def reorder_acceptance_criteria(
        self, task_id: str, criterion_id: str, new_order: int
    ) -> DomainResult[Dict[str, Any]]:
        """Change acceptance criterion order."""
        current = self.get_acceptance_criterion(task_id, criterion_id)
        if current.is_failure:
            return current

        assoc_result = self.memory_association_repo.get_by_entity(criterion_id)
        if assoc_result.is_failure:
            return assoc_result

        update_result = self.memory_association_repo.update(
            assoc_result.data.id, {"order_index": new_order}
        )
        if update_result.is_failure:
            return update_result

        return self.get_acceptance_criterion(task_id, criterion_id)

    # --- Task Testing Strategy CRUD Operations ---

    def list_testing_steps(self, task_id: str) -> DomainResult[Dict[str, Any]]:
        """List all testing steps for a task."""
        task_result = self.task_repo.get(task_id)
        if task_result.is_failure:
            return task_result

        steps = self._get_task_testing_steps(task_id)
        return DomainSuccess.create(data={"task_id": task_id, "steps": steps})

    def get_testing_step(self, task_id: str, step_id: str) -> DomainResult[Dict[str, Any]]:
        """Get a single testing step."""
        task_result = self.task_repo.get(task_id)
        if task_result.is_failure:
            return task_result

        entity_result = self.memory_entity_repo.get(step_id)
        if entity_result.is_failure:
            return DomainError.not_found("Testing step", step_id)

        entity = entity_result.data
        observations = entity.observations
        content = observations[0] if observations else ""
        step_type = entity.metadata.get("step_type", "verify")
        test_status = entity.metadata.get("test_status", "pending")

        return DomainSuccess.create(
            data={
                "id": entity.id,
                "task_id": task_id,
                "content": content,
                "step_type": step_type,
                "test_status": test_status,
            }
        )

    def update_testing_step(
        self,
        task_id: str,
        step_id: str,
        content: Optional[str] = None,
        step_type: Optional[str] = None,
    ) -> DomainResult[Dict[str, Any]]:
        """Update a testing step."""
        current = self.get_testing_step(task_id, step_id)
        if current.is_failure:
            return current

        updates: Dict[str, Any] = {}
        if content is not None:
            updates["observations"] = [content]

        if step_type is not None:
            entity_result = self.memory_entity_repo.get(step_id)
            if entity_result.is_success:
                metadata = entity_result.data.metadata or {}
                metadata["step_type"] = step_type
                updates["metadata"] = metadata

        if not updates:
            return current

        update_result = self.memory_entity_repo.update(step_id, updates)
        if update_result.is_failure:
            return update_result

        return self.get_testing_step(task_id, step_id)

    def delete_testing_step(self, task_id: str, step_id: str) -> DomainResult[Dict[str, Any]]:
        """Delete a testing step."""
        current = self.get_testing_step(task_id, step_id)
        if current.is_failure:
            return current

        delete_result = self.memory_entity_repo.delete(step_id)
        if delete_result.is_failure:
            return delete_result

        return DomainSuccess.create(
            data={
                "deleted": True,
                "step_id": step_id,
                "task_id": task_id,
            }
        )

    def mark_testing_step_passed(self, task_id: str, step_id: str) -> DomainResult[Dict[str, Any]]:
        """Mark a testing step as passed."""
        return self._update_testing_step_status(task_id, step_id, "passed")

    def mark_testing_step_failed(self, task_id: str, step_id: str) -> DomainResult[Dict[str, Any]]:
        """Mark a testing step as failed."""
        return self._update_testing_step_status(task_id, step_id, "failed")

    def mark_testing_step_skipped(self, task_id: str, step_id: str) -> DomainResult[Dict[str, Any]]:
        """Mark a testing step as skipped."""
        return self._update_testing_step_status(task_id, step_id, "skipped")

    def _update_testing_step_status(
        self, task_id: str, step_id: str, status: str
    ) -> DomainResult[Dict[str, Any]]:
        """Update testing step status (internal helper)."""
        current = self.get_testing_step(task_id, step_id)
        if current.is_failure:
            return current

        entity_result = self.memory_entity_repo.get(step_id)
        if entity_result.is_failure:
            return entity_result

        metadata = entity_result.data.metadata or {}
        metadata["test_status"] = status

        update_result = self.memory_entity_repo.update(step_id, {"metadata": metadata})
        if update_result.is_failure:
            return update_result

        return self.get_testing_step(task_id, step_id)

    def reorder_testing_steps(
        self, task_id: str, step_id: str, new_order: int
    ) -> DomainResult[Dict[str, Any]]:
        """Change testing step order."""
        current = self.get_testing_step(task_id, step_id)
        if current.is_failure:
            return current

        assoc_result = self.memory_association_repo.get_by_entity(step_id)
        if assoc_result.is_failure:
            return assoc_result

        update_result = self.memory_association_repo.update(
            assoc_result.data.id, {"order_index": new_order}
        )
        if update_result.is_failure:
            return update_result

        return self.get_testing_step(task_id, step_id)

    # --- Bulk Operations ---

    def bulk_add_research(
        self,
        task_ids: List[str],
        research_items: List[Dict[str, Any]],
    ) -> DomainResult[Dict[str, Any]]:
        """Add research items to multiple tasks atomically.

        Adds ALL research items to ALL specified tasks.

        Args:
            task_ids: List of task IDs to add research to.
            research_items: List of research item dicts with content and type.

        Returns:
            DomainResult with summary of operations performed.
        """
        if not task_ids:
            return DomainError.validation_error("task_ids must be non-empty")
        if not research_items:
            return DomainError.validation_error("research_items must be non-empty")

        # Validate all tasks exist
        for tid in task_ids:
            result = self.task_repo.get_task(tid)
            if result.is_failure:
                return DomainError.not_found("task", tid)

        total_added = 0
        for tid in task_ids:
            for item in research_items:
                content = item.get("content", "")
                research_type = item.get("type", "findings")
                if not content:
                    continue
                add_result = self.add_research(tid, content, research_type)
                if add_result.is_failure:
                    return add_result
                total_added += 1

        return DomainSuccess.create({
            "tasks_updated": len(task_ids),
            "research_added_per_task": len(research_items),
            "total_research_added": total_added,
            "task_ids": task_ids,
        })

    def bulk_add_details(
        self,
        tasks: List[Dict[str, Any]],
    ) -> DomainResult[Dict[str, Any]]:
        """Add different details to multiple tasks atomically.

        Each task receives its own specific research, notes, criteria, and testing steps.

        Args:
            tasks: List of dicts with task_id and optional research, notes, criteria, testing_strategy.

        Returns:
            DomainResult with per-task summary.
        """
        if not tasks:
            return DomainError.validation_error("tasks must be non-empty")

        details: List[Dict[str, Any]] = []
        success_count = 0
        failed_count = 0

        for task_entry in tasks:
            tid = task_entry.get("task_id", "")
            if not tid:
                failed_count += 1
                continue

            # Validate task exists
            task_result = self.task_repo.get_task(tid)
            if task_result.is_failure:
                failed_count += 1
                continue

            task_detail: Dict[str, Any] = {
                "task_id": tid, "research": 0, "notes": 0, "criteria": 0, "testing_steps": 0,
            }

            # Add research
            for item in task_entry.get("research", []):
                content = item.get("content", "")
                research_type = item.get("type", "findings")
                if content:
                    r = self.add_research(tid, content, research_type)
                    if r.is_success:
                        task_detail["research"] += 1

            # Add notes
            for item in task_entry.get("notes", []):
                content = item.get("content", "")
                if content:
                    r = self.add_implementation_note(tid, content)
                    if r.is_success:
                        task_detail["notes"] += 1

            # Add criteria
            for criterion in task_entry.get("criteria", []):
                if isinstance(criterion, str) and criterion:
                    r = self.add_acceptance_criteria(tid, criterion)
                    if r.is_success:
                        task_detail["criteria"] += 1

            # Add testing strategy steps
            for step in task_entry.get("testing_strategy", []):
                content = step.get("content", "")
                step_type = step.get("step_type", "verify")
                if content:
                    r = self.add_testing_step(tid, content, step_type)
                    if r.is_success:
                        task_detail["testing_steps"] += 1

            details.append(task_detail)
            success_count += 1

        return DomainSuccess.create({
            "success_count": success_count,
            "failed_count": failed_count,
            "details": details,
        })
