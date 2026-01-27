"""
Task Repository.

SQLAlchemy ORM-based repository for task operations.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import case, select

from task_crusade_mcp.database.models.task import Task
from task_crusade_mcp.database.orm_manager import ORMManager, get_orm_manager
from task_crusade_mcp.domain.entities.result_types import (
    DomainError,
    DomainResult,
    DomainSuccess,
)
from task_crusade_mcp.domain.entities.task import TaskDTO


class TaskRepository:
    """
    Task repository using SQLAlchemy ORM.

    Provides CRUD operations for tasks with proper error handling
    via DomainResult pattern.
    """

    def __init__(self, orm_manager: Optional[ORMManager] = None):
        """
        Initialize repository with ORM manager.

        Args:
            orm_manager: ORM manager instance. Uses singleton if not provided.
        """
        self.orm_manager = orm_manager or get_orm_manager()

    def _to_dto(self, task: Task) -> TaskDTO:
        """Convert Task model to TaskDTO."""
        return TaskDTO(
            id=task.id,
            title=task.title,
            description=task.description,
            priority=task.priority,
            status=task.status,
            category=task.category,
            type=task.type,
            created_at=task.created_at,
            updated_at=task.updated_at,
            completed_at=task.completed_at,
            tags=task.get_tags(),
            dependencies=task.get_dependencies(),
            failure_reason=task.failure_reason,
            campaign_id=task.campaign_id,
            priority_order=task.priority_order,
        )

    def create(self, task_data: Dict[str, Any]) -> DomainResult[TaskDTO]:
        """
        Create a new task.

        Args:
            task_data: Dictionary containing task fields.

        Returns:
            DomainResult with created task data.
        """
        try:
            with self.orm_manager.get_session() as session:
                # Create task
                task = Task(
                    title=task_data.get("title", ""),
                    description=task_data.get("description"),
                    priority=task_data.get("priority", "medium"),
                    status=task_data.get("status", "pending"),
                    category=task_data.get("category"),
                    type=task_data.get("type", "code"),
                    campaign_id=task_data.get("campaign_id"),
                    priority_order=task_data.get("priority_order"),
                    failure_reason=task_data.get("failure_reason"),
                )

                # Set tags if provided
                if "tags" in task_data:
                    tags = task_data["tags"]
                    if isinstance(tags, str):
                        task.tags_json = tags
                    else:
                        task.set_tags(tags or [])

                # Set dependencies if provided
                if "dependencies" in task_data:
                    deps = task_data["dependencies"]
                    if isinstance(deps, str):
                        task.dependencies_json = deps
                    else:
                        task.set_dependencies(deps or [])

                session.add(task)
                session.flush()

                return DomainSuccess.create(data=self._to_dto(task))

        except Exception as e:
            return DomainError.operation_failed("create_task", str(e))

    def get(self, task_id: str) -> DomainResult[TaskDTO]:
        """
        Get task by ID.

        Args:
            task_id: Task UUID.

        Returns:
            DomainResult with task data or not found error.
        """
        try:
            with self.orm_manager.get_session() as session:
                task = session.execute(select(Task).where(Task.id == task_id)).scalar_one_or_none()

                if not task:
                    return DomainError.not_found("Task", task_id)

                return DomainSuccess.create(data=self._to_dto(task))

        except Exception as e:
            return DomainError.operation_failed("get_task", str(e))

    def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> DomainResult[List[TaskDTO]]:
        """
        List tasks with optional filtering.

        Args:
            filters: Dictionary of field filters.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            DomainResult with list of task DTOs.
        """
        try:
            with self.orm_manager.get_session() as session:
                query = select(Task)

                # Apply filters
                if filters:
                    if "campaign_id" in filters:
                        query = query.where(Task.campaign_id == filters["campaign_id"])
                    if "status" in filters:
                        query = query.where(Task.status == filters["status"])
                    if "priority" in filters:
                        query = query.where(Task.priority == filters["priority"])
                    if "category" in filters:
                        query = query.where(Task.category == filters["category"])
                    if "type" in filters:
                        query = query.where(Task.type == filters["type"])

                # Apply ordering
                query = query.order_by(Task.priority_order.asc().nullslast(), Task.created_at.asc())

                if limit:
                    query = query.limit(limit)
                if offset:
                    query = query.offset(offset)

                tasks = session.execute(query).scalars().all()
                return DomainSuccess.create(data=[self._to_dto(t) for t in tasks])

        except Exception as e:
            return DomainError.operation_failed("list_tasks", str(e))

    def update(self, task_id: str, updates: Dict[str, Any]) -> DomainResult[TaskDTO]:
        """
        Update a task.

        Args:
            task_id: Task UUID.
            updates: Dictionary of fields to update.

        Returns:
            DomainResult with updated task data.
        """
        try:
            with self.orm_manager.get_session() as session:
                task = session.execute(select(Task).where(Task.id == task_id)).scalar_one_or_none()

                if not task:
                    return DomainError.not_found("Task", task_id)

                # Apply updates
                for field, value in updates.items():
                    if field == "tags":
                        if isinstance(value, str):
                            task.tags_json = value
                        else:
                            task.set_tags(value or [])
                    elif field == "dependencies":
                        if isinstance(value, str):
                            task.dependencies_json = value
                        else:
                            task.set_dependencies(value or [])
                    elif hasattr(task, field) and field not in ("id", "created_at"):
                        setattr(task, field, value)

                # Handle status change to terminal states (done or cancelled)
                terminal_task_states = {"done", "cancelled"}
                new_status = updates.get("status")
                if new_status in terminal_task_states and not task.completed_at:
                    task.completed_at = datetime.now(timezone.utc)

                session.flush()
                return DomainSuccess.create(data=self._to_dto(task))

        except Exception as e:
            return DomainError.operation_failed("update_task", str(e))

    def delete(self, task_id: str) -> DomainResult[Dict[str, Any]]:
        """
        Delete a task.

        Args:
            task_id: Task UUID.

        Returns:
            DomainResult with deletion confirmation.
        """
        try:
            with self.orm_manager.get_session() as session:
                task = session.execute(select(Task).where(Task.id == task_id)).scalar_one_or_none()

                if not task:
                    return DomainError.not_found("Task", task_id)

                session.delete(task)
                session.flush()

                return DomainSuccess.create(
                    data={
                        "task_id": task_id,
                        "message": f"Task '{task_id}' deleted successfully",
                    }
                )

        except Exception as e:
            return DomainError.operation_failed("delete_task", str(e))

    def get_by_campaign(
        self,
        campaign_id: str,
        status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> DomainResult[List[TaskDTO]]:
        """
        Get tasks for a campaign.

        Args:
            campaign_id: Campaign UUID.
            status: Optional status filter.
            limit: Maximum number of results.

        Returns:
            DomainResult with list of task DTOs.
        """
        filters = {"campaign_id": campaign_id}
        if status:
            filters["status"] = status
        return self.list(filters=filters, limit=limit)

    def get_actionable_tasks(
        self,
        campaign_id: str,
        max_results: int = 10,
    ) -> DomainResult[List[TaskDTO]]:
        """
        Get actionable tasks (dependencies met) for a campaign.

        Finds tasks that are pending or in-progress with all dependencies in "done" status.

        Args:
            campaign_id: Campaign UUID.
            max_results: Maximum number of tasks to return.

        Returns:
            DomainResult with list of actionable task DTOs.
        """
        try:
            with self.orm_manager.get_session() as session:
                # Get all tasks for the campaign
                tasks = (
                    session.execute(
                        select(Task)
                        .where(
                            Task.campaign_id == campaign_id,
                            Task.status.in_(["pending", "in-progress"]),
                        )
                        .order_by(
                            case((Task.status == "in-progress", 0), else_=1),
                            case(
                                (Task.priority == "critical", 1),
                                (Task.priority == "high", 2),
                                (Task.priority == "medium", 3),
                                (Task.priority == "low", 4),
                                else_=5,
                            ),
                            Task.priority_order.asc().nullslast(),
                            Task.created_at.asc(),
                        )
                    )
                    .scalars()
                    .all()
                )

                # Get all task statuses for dependency checking
                all_tasks = session.execute(
                    select(Task.id, Task.status).where(Task.campaign_id == campaign_id)
                ).all()
                task_status_map = {t.id: t.status for t in all_tasks}

                # Filter to actionable tasks (all dependencies done)
                actionable = []
                for task in tasks:
                    dependencies = task.get_dependencies()
                    if not dependencies:
                        actionable.append(task)
                    else:
                        all_deps_done = all(
                            task_status_map.get(dep_id) == "done" for dep_id in dependencies
                        )
                        if all_deps_done:
                            actionable.append(task)

                    if len(actionable) >= max_results:
                        break

                return DomainSuccess.create(data=[self._to_dto(t) for t in actionable])

        except Exception as e:
            return DomainError.operation_failed("get_actionable_tasks", str(e))

    def get_next_actionable_task(
        self,
        campaign_id: str,
    ) -> DomainResult[Optional[TaskDTO]]:
        """
        Get the next actionable task for a campaign.

        Args:
            campaign_id: Campaign UUID.

        Returns:
            DomainResult with the next actionable task DTO or None.
        """
        result = self.get_actionable_tasks(campaign_id, max_results=1)
        if result.is_failure:
            return result

        tasks = result.data or []
        if tasks:
            return DomainSuccess.create(data=tasks[0])
        return DomainSuccess.create(data=None)
