"""
Memory Task Association Repository.

SQLAlchemy ORM-based repository for memory task association operations.
Used internally by task services - not exposed via MCP.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import func, select

from task_crusade_mcp.database.models.memory import MemoryTaskAssociation
from task_crusade_mcp.database.orm_manager import ORMManager, get_orm_manager
from task_crusade_mcp.domain.entities.memory import MemoryTaskAssociationDTO
from task_crusade_mcp.domain.entities.result_types import (
    DomainError,
    DomainResult,
    DomainSuccess,
)


class MemoryAssociationRepository:
    """
    Memory Task Association repository using SQLAlchemy ORM.

    Provides CRUD operations for memory task associations with proper error handling
    via DomainResult pattern.
    """

    def __init__(self, orm_manager: Optional[ORMManager] = None):
        """Initialize repository with ORM manager."""
        self.orm_manager = orm_manager or get_orm_manager()

    def _to_dto(self, assoc: MemoryTaskAssociation) -> MemoryTaskAssociationDTO:
        """Convert MemoryTaskAssociation model to MemoryTaskAssociationDTO."""
        return MemoryTaskAssociationDTO(
            id=assoc.id,
            memory_entity_id=assoc.memory_entity_id,
            task_id=assoc.task_id,
            campaign_id=assoc.campaign_id,
            association_type=assoc.association_type,
            notes=assoc.notes,
            order_index=assoc.order_index,
            created_at=assoc.created_at,
            updated_at=assoc.updated_at,
        )

    def create(self, association_data: Dict[str, Any]) -> DomainResult[MemoryTaskAssociationDTO]:
        """Create a new memory task association."""
        try:
            with self.orm_manager.get_session() as session:
                # Get the next order_index for the task/campaign
                task_id = association_data.get("task_id")
                campaign_id = association_data.get("campaign_id")
                assoc_type = association_data.get("association_type")

                # Calculate next order_index
                query = select(func.max(MemoryTaskAssociation.order_index))
                if task_id:
                    query = query.where(
                        MemoryTaskAssociation.task_id == task_id,
                        MemoryTaskAssociation.association_type == assoc_type,
                    )
                else:
                    query = query.where(
                        MemoryTaskAssociation.campaign_id == campaign_id,
                        MemoryTaskAssociation.association_type == assoc_type,
                    )

                max_order = session.scalar(query)
                next_order = (max_order or 0) + 1

                assoc = MemoryTaskAssociation(
                    memory_entity_id=association_data.get("memory_entity_id"),
                    task_id=task_id,
                    campaign_id=campaign_id,
                    association_type=assoc_type or "reference",
                    notes=association_data.get("notes"),
                    order_index=association_data.get("order_index", next_order),
                )

                session.add(assoc)
                session.flush()

                return DomainSuccess.create(data=self._to_dto(assoc))

        except Exception as e:
            return DomainError.operation_failed("create_memory_association", str(e))

    def get(self, association_id: str) -> DomainResult[MemoryTaskAssociationDTO]:
        """Get memory task association by ID."""
        try:
            with self.orm_manager.get_session() as session:
                assoc = session.execute(
                    select(MemoryTaskAssociation).where(MemoryTaskAssociation.id == association_id)
                ).scalar_one_or_none()

                if not assoc:
                    return DomainError.not_found("MemoryTaskAssociation", association_id)

                return DomainSuccess.create(data=self._to_dto(assoc))

        except Exception as e:
            return DomainError.operation_failed("get_memory_association", str(e))

    def list_by_task(
        self,
        task_id: str,
        association_type: Optional[str] = None,
    ) -> DomainResult[List[MemoryTaskAssociationDTO]]:
        """List associations for a task."""
        try:
            with self.orm_manager.get_session() as session:
                query = select(MemoryTaskAssociation).where(
                    MemoryTaskAssociation.task_id == task_id
                )

                if association_type:
                    query = query.where(MemoryTaskAssociation.association_type == association_type)

                query = query.order_by(MemoryTaskAssociation.order_index.asc())

                assocs = session.execute(query).scalars().all()
                return DomainSuccess.create(data=[self._to_dto(a) for a in assocs])

        except Exception as e:
            return DomainError.operation_failed("list_memory_associations_by_task", str(e))

    def list_by_campaign(
        self,
        campaign_id: str,
        association_type: Optional[str] = None,
    ) -> DomainResult[List[MemoryTaskAssociationDTO]]:
        """List associations for a campaign."""
        try:
            with self.orm_manager.get_session() as session:
                query = select(MemoryTaskAssociation).where(
                    MemoryTaskAssociation.campaign_id == campaign_id
                )

                if association_type:
                    query = query.where(MemoryTaskAssociation.association_type == association_type)

                query = query.order_by(MemoryTaskAssociation.order_index.asc())

                assocs = session.execute(query).scalars().all()
                return DomainSuccess.create(data=[self._to_dto(a) for a in assocs])

        except Exception as e:
            return DomainError.operation_failed("list_memory_associations_by_campaign", str(e))

    def update(
        self, association_id: str, updates: Dict[str, Any]
    ) -> DomainResult[MemoryTaskAssociationDTO]:
        """Update a memory task association."""
        try:
            with self.orm_manager.get_session() as session:
                assoc = session.execute(
                    select(MemoryTaskAssociation).where(MemoryTaskAssociation.id == association_id)
                ).scalar_one_or_none()

                if not assoc:
                    return DomainError.not_found("MemoryTaskAssociation", association_id)

                for field, value in updates.items():
                    if hasattr(assoc, field) and field not in ("id", "created_at"):
                        setattr(assoc, field, value)

                session.flush()
                return DomainSuccess.create(data=self._to_dto(assoc))

        except Exception as e:
            return DomainError.operation_failed("update_memory_association", str(e))

    def delete(self, association_id: str) -> DomainResult[Dict[str, Any]]:
        """Delete a memory task association."""
        try:
            with self.orm_manager.get_session() as session:
                assoc = session.execute(
                    select(MemoryTaskAssociation).where(MemoryTaskAssociation.id == association_id)
                ).scalar_one_or_none()

                if not assoc:
                    return DomainError.not_found("MemoryTaskAssociation", association_id)

                session.delete(assoc)
                session.flush()

                return DomainSuccess.create(
                    data={
                        "association_id": association_id,
                        "message": f"MemoryTaskAssociation '{association_id}' deleted",
                    }
                )

        except Exception as e:
            return DomainError.operation_failed("delete_memory_association", str(e))

    def reorder(
        self, association_id: str, new_order: int
    ) -> DomainResult[MemoryTaskAssociationDTO]:
        """Update the order position of an association."""
        return self.update(association_id, {"order_index": new_order})
