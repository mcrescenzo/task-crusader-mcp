"""
Campaign Repository.

SQLAlchemy ORM-based repository for campaign operations.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import case, func, select

from task_crusade_mcp.database.models.campaign import Campaign
from task_crusade_mcp.database.models.task import Task
from task_crusade_mcp.database.orm_manager import ORMManager, get_orm_manager
from task_crusade_mcp.domain.entities.campaign import CampaignDTO
from task_crusade_mcp.domain.entities.result_types import (
    DomainError,
    DomainResult,
    DomainSuccess,
)


class CampaignRepository:
    """
    Campaign repository using SQLAlchemy ORM.

    Provides CRUD operations for campaigns with proper error handling
    via DomainResult pattern.
    """

    def __init__(self, orm_manager: Optional[ORMManager] = None):
        """
        Initialize repository with ORM manager.

        Args:
            orm_manager: ORM manager instance. Uses singleton if not provided.
        """
        self.orm_manager = orm_manager or get_orm_manager()

    def _to_dto(self, campaign: Campaign) -> CampaignDTO:
        """Convert Campaign model to CampaignDTO."""
        return CampaignDTO(
            id=campaign.id,
            name=campaign.name,
            description=campaign.description,
            status=campaign.status,
            priority=campaign.priority,
            metadata=campaign.get_metadata(),
            created_at=campaign.created_at,
            updated_at=campaign.updated_at,
            completed_at=campaign.completed_at,
        )

    def create_campaign(self, campaign_data: Dict[str, Any]) -> DomainResult[CampaignDTO]:
        """
        Create a new campaign.

        Args:
            campaign_data: Dictionary containing campaign fields.

        Returns:
            DomainResult with created campaign data.
        """
        try:
            with self.orm_manager.get_session() as session:
                # Check for duplicate name
                existing = session.execute(
                    select(Campaign).where(Campaign.name == campaign_data.get("name"))
                ).scalar_one_or_none()

                if existing:
                    return DomainError.already_exists("Campaign", campaign_data.get("name", ""))

                # Create campaign
                campaign = Campaign(
                    name=campaign_data.get("name"),
                    description=campaign_data.get("description", ""),
                    status=campaign_data.get("status", "planning"),
                    priority=campaign_data.get("priority", "medium"),
                )

                # Set metadata if provided
                metadata = campaign_data.get("metadata", {})
                if campaign_data.get("title"):
                    metadata["title"] = campaign_data["title"]
                if campaign_data.get("owner"):
                    metadata["owner"] = campaign_data["owner"]
                if metadata:
                    campaign.set_metadata(metadata)

                session.add(campaign)
                session.flush()

                return DomainSuccess.create(data=self._to_dto(campaign))

        except Exception as e:
            return DomainError.operation_failed("create_campaign", str(e))

    def get(self, campaign_id: str) -> DomainResult[CampaignDTO]:
        """
        Get campaign by ID.

        Args:
            campaign_id: Campaign UUID.

        Returns:
            DomainResult with campaign data or not found error.
        """
        try:
            with self.orm_manager.get_session() as session:
                campaign = session.execute(
                    select(Campaign).where(Campaign.id == campaign_id)
                ).scalar_one_or_none()

                if not campaign:
                    return DomainError.not_found("Campaign", campaign_id)

                return DomainSuccess.create(data=self._to_dto(campaign))

        except Exception as e:
            return DomainError.operation_failed("get_campaign", str(e))

    def get_by_name(self, name: str) -> DomainResult[CampaignDTO]:
        """
        Get campaign by name.

        Args:
            name: Campaign name.

        Returns:
            DomainResult with campaign data or not found error.
        """
        try:
            with self.orm_manager.get_session() as session:
                campaign = session.execute(
                    select(Campaign).where(Campaign.name == name)
                ).scalar_one_or_none()

                if not campaign:
                    return DomainError.not_found("Campaign", name)

                return DomainSuccess.create(data=self._to_dto(campaign))

        except Exception as e:
            return DomainError.operation_failed("get_campaign_by_name", str(e))

    def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> DomainResult[List[Dict[str, Any]]]:
        """
        List campaigns with optional filtering.

        Args:
            filters: Dictionary of field filters.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            DomainResult with list of campaign dictionaries.
        """
        try:
            with self.orm_manager.get_session() as session:
                query = select(Campaign)

                # Apply filters
                if filters:
                    if "status" in filters:
                        query = query.where(Campaign.status == filters["status"])
                    if "priority" in filters:
                        query = query.where(Campaign.priority == filters["priority"])

                # Apply ordering and pagination
                query = query.order_by(Campaign.created_at.desc())

                if limit:
                    query = query.limit(limit)
                if offset:
                    query = query.offset(offset)

                campaigns = session.execute(query).scalars().all()

                result_data = []
                for campaign in campaigns:
                    campaign_dict = self._to_dto(campaign).to_dict()

                    # Add task statistics
                    stats = self._get_task_statistics(session, campaign.id)
                    campaign_dict["task_statistics"] = stats

                    result_data.append(campaign_dict)

                return DomainSuccess.create(data=result_data)

        except Exception as e:
            return DomainError.operation_failed("list_campaigns", str(e))

    def _get_task_statistics(self, session: Any, campaign_id: str) -> Dict[str, Any]:
        """Get task statistics for a campaign."""
        stats = session.execute(
            select(
                func.count(Task.id).label("total"),
                func.sum(case((Task.status == "done", 1), else_=0)).label("completed"),
                func.sum(case((Task.status == "in-progress", 1), else_=0)).label("in_progress"),
                func.sum(case((Task.status == "pending", 1), else_=0)).label("pending"),
                func.sum(case((Task.status == "blocked", 1), else_=0)).label("blocked"),
            ).where(Task.campaign_id == campaign_id)
        ).one()

        total = stats.total or 0
        completed = stats.completed or 0

        return {
            "total": total,
            "by_status": {
                "done": completed,
                "in-progress": stats.in_progress or 0,
                "pending": stats.pending or 0,
                "blocked": stats.blocked or 0,
            },
            "completed_percentage": (completed / total * 100) if total > 0 else 0.0,
        }

    def update(self, campaign_id: str, updates: Dict[str, Any]) -> DomainResult[CampaignDTO]:
        """
        Update a campaign.

        Args:
            campaign_id: Campaign UUID.
            updates: Dictionary of fields to update.

        Returns:
            DomainResult with updated campaign data.
        """
        try:
            with self.orm_manager.get_session() as session:
                campaign = session.execute(
                    select(Campaign).where(Campaign.id == campaign_id)
                ).scalar_one_or_none()

                if not campaign:
                    return DomainError.not_found("Campaign", campaign_id)

                # Apply updates
                for field, value in updates.items():
                    if hasattr(campaign, field) and field not in ("id", "created_at"):
                        setattr(campaign, field, value)

                session.flush()
                return DomainSuccess.create(data=self._to_dto(campaign))

        except Exception as e:
            return DomainError.operation_failed("update_campaign", str(e))

    def delete(self, campaign_id: str) -> DomainResult[Dict[str, Any]]:
        """
        Delete a campaign and all its tasks.

        Args:
            campaign_id: Campaign UUID.

        Returns:
            DomainResult with deletion confirmation.
        """
        try:
            with self.orm_manager.get_session() as session:
                campaign = session.execute(
                    select(Campaign).where(Campaign.id == campaign_id)
                ).scalar_one_or_none()

                if not campaign:
                    return DomainError.not_found("Campaign", campaign_id)

                # Count tasks before deletion
                task_count = session.scalar(
                    select(func.count(Task.id)).where(Task.campaign_id == campaign_id)
                )

                # Delete campaign (cascade deletes tasks)
                session.delete(campaign)
                session.flush()

                return DomainSuccess.create(
                    data={
                        "campaign_id": campaign_id,
                        "tasks_deleted": task_count or 0,
                        "message": f"Campaign '{campaign_id}' deleted successfully",
                    }
                )

        except Exception as e:
            return DomainError.operation_failed("delete_campaign", str(e))

    def get_progress_summary(self, campaign_id: str) -> DomainResult[Dict[str, Any]]:
        """
        Get lightweight progress summary for a campaign.

        Args:
            campaign_id: Campaign UUID.

        Returns:
            DomainResult with progress summary.
        """
        try:
            with self.orm_manager.get_session() as session:
                # Verify campaign exists
                campaign = session.execute(
                    select(Campaign).where(Campaign.id == campaign_id)
                ).scalar_one_or_none()

                if not campaign:
                    return DomainError.not_found("Campaign", campaign_id)

                # Get task counts by status
                status_counts = session.execute(
                    select(Task.status, func.count(Task.id).label("count"))
                    .where(Task.campaign_id == campaign_id)
                    .group_by(Task.status)
                ).all()

                # Build status dictionary
                tasks_by_status = {
                    "pending": 0,
                    "in-progress": 0,
                    "done": 0,
                    "cancelled": 0,
                    "blocked": 0,
                }
                total_tasks = 0

                for status, count in status_counts:
                    tasks_by_status[status] = count
                    total_tasks += count

                # Calculate completion rate
                completed_count = tasks_by_status.get("done", 0)
                completion_rate = (completed_count / total_tasks * 100) if total_tasks > 0 else 0.0

                # Get current in-progress task
                current_in_progress = (
                    session.execute(
                        select(Task)
                        .where(Task.campaign_id == campaign_id, Task.status == "in-progress")
                        .order_by(Task.updated_at.desc())
                    )
                    .scalars()
                    .first()
                )

                current_in_progress_task = None
                if current_in_progress:
                    current_in_progress_task = {
                        "id": current_in_progress.id,
                        "title": current_in_progress.title,
                        "priority": current_in_progress.priority,
                    }

                # Get next actionable task
                next_pending = (
                    session.execute(
                        select(Task)
                        .where(Task.campaign_id == campaign_id, Task.status == "pending")
                        .order_by(
                            case(
                                (Task.priority == "high", 1),
                                (Task.priority == "medium", 2),
                                (Task.priority == "low", 3),
                                else_=4,
                            ),
                            Task.priority_order.asc().nullslast(),
                            Task.created_at.asc(),
                        )
                    )
                    .scalars()
                    .first()
                )

                next_actionable_task = None
                if next_pending:
                    next_actionable_task = {
                        "id": next_pending.id,
                        "title": next_pending.title,
                        "priority": next_pending.priority,
                    }

                return DomainSuccess.create(
                    data={
                        "campaign_id": campaign_id,
                        "campaign_name": campaign.name,
                        "total_tasks": total_tasks,
                        "tasks_by_status": tasks_by_status,
                        "completion_rate": round(completion_rate, 2),
                        "current_in_progress_task": current_in_progress_task,
                        "next_actionable_task": next_actionable_task,
                    }
                )

        except Exception as e:
            return DomainError.operation_failed("get_progress_summary", str(e))

    def get_campaign_with_tasks(
        self, campaign_id: str, include_task_details: bool = True
    ) -> DomainResult[Dict[str, Any]]:
        """
        Get campaign with associated tasks.

        Args:
            campaign_id: Campaign UUID.
            include_task_details: Whether to include full task details.

        Returns:
            DomainResult with campaign and tasks data.
        """
        try:
            with self.orm_manager.get_session() as session:
                campaign = session.execute(
                    select(Campaign).where(Campaign.id == campaign_id)
                ).scalar_one_or_none()

                if not campaign:
                    return DomainError.not_found("Campaign", campaign_id)

                campaign_data = self._to_dto(campaign).to_dict()

                # Get associated tasks
                if include_task_details:
                    tasks = (
                        session.execute(
                            select(Task)
                            .where(Task.campaign_id == campaign_id)
                            .order_by(Task.priority_order.asc().nullslast(), Task.created_at.asc())
                        )
                        .scalars()
                        .all()
                    )
                    campaign_data["tasks"] = [task.to_dict() for task in tasks]
                else:
                    tasks = session.execute(
                        select(Task.id, Task.title, Task.status, Task.priority)
                        .where(Task.campaign_id == campaign_id)
                        .order_by(Task.priority_order.asc().nullslast(), Task.created_at.asc())
                    ).all()
                    campaign_data["tasks"] = [
                        {"id": t.id, "title": t.title, "status": t.status, "priority": t.priority}
                        for t in tasks
                    ]

                return DomainSuccess.create(data=campaign_data)

        except Exception as e:
            return DomainError.operation_failed("get_campaign_with_tasks", str(e))


def resolve_campaign_id(
    campaign_identifier: str, campaign_repo: CampaignRepository
) -> Optional[str]:
    """
    Resolve campaign identifier to UUID.

    Args:
        campaign_identifier: Either campaign UUID or campaign name.
        campaign_repo: Campaign repository instance.

    Returns:
        Campaign UUID if found, None otherwise.
    """
    import re

    # Check if already a UUID
    uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    if re.match(uuid_pattern, campaign_identifier, re.IGNORECASE):
        result = campaign_repo.get(campaign_identifier)
        if result.is_success:
            return campaign_identifier
        return None

    # Try to resolve by name
    result = campaign_repo.get_by_name(campaign_identifier)
    if result.is_success and result.data:
        return result.data.id

    return None
