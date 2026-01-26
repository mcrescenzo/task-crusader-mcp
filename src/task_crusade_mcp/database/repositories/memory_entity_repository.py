"""
Memory Entity Repository.

SQLAlchemy ORM-based repository for memory entity operations.
Used internally by task services - not exposed via MCP.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import select

from task_crusade_mcp.database.models.memory import MemoryEntity
from task_crusade_mcp.database.orm_manager import ORMManager, get_orm_manager
from task_crusade_mcp.domain.entities.memory import MemoryEntityDTO
from task_crusade_mcp.domain.entities.result_types import (
    DomainError,
    DomainResult,
    DomainSuccess,
)


class MemoryEntityRepository:
    """
    Memory Entity repository using SQLAlchemy ORM.

    Provides CRUD operations for memory entities with proper error handling
    via DomainResult pattern.
    """

    def __init__(self, orm_manager: Optional[ORMManager] = None):
        """Initialize repository with ORM manager."""
        self.orm_manager = orm_manager or get_orm_manager()

    def _to_dto(self, entity: MemoryEntity) -> MemoryEntityDTO:
        """Convert MemoryEntity model to MemoryEntityDTO."""
        return MemoryEntityDTO(
            id=entity.id,
            session_id=entity.session_id,
            name=entity.name,
            entity_type=entity.entity_type,
            observations=entity.get_observations(),
            metadata=entity.get_metadata(),
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def create(self, entity_data: Dict[str, Any]) -> DomainResult[MemoryEntityDTO]:
        """Create a new memory entity."""
        try:
            with self.orm_manager.get_session() as session:
                entity = MemoryEntity(
                    session_id=entity_data.get("session_id"),
                    name=entity_data.get("name", ""),
                    entity_type=entity_data.get("entity_type", ""),
                )

                if entity_data.get("observations"):
                    entity.set_observations(entity_data["observations"])
                if entity_data.get("metadata"):
                    entity.set_metadata(entity_data["metadata"])

                session.add(entity)
                session.flush()

                return DomainSuccess.create(data=self._to_dto(entity))

        except Exception as e:
            return DomainError.operation_failed("create_memory_entity", str(e))

    def get(self, entity_id: str) -> DomainResult[MemoryEntityDTO]:
        """Get memory entity by ID."""
        try:
            with self.orm_manager.get_session() as session:
                entity = session.execute(
                    select(MemoryEntity).where(MemoryEntity.id == entity_id)
                ).scalar_one_or_none()

                if not entity:
                    return DomainError.not_found("MemoryEntity", entity_id)

                return DomainSuccess.create(data=self._to_dto(entity))

        except Exception as e:
            return DomainError.operation_failed("get_memory_entity", str(e))

    def get_by_session_and_name(self, session_id: str, name: str) -> DomainResult[MemoryEntityDTO]:
        """Get memory entity by session and name."""
        try:
            with self.orm_manager.get_session() as session:
                entity = session.execute(
                    select(MemoryEntity).where(
                        MemoryEntity.session_id == session_id,
                        MemoryEntity.name == name,
                    )
                ).scalar_one_or_none()

                if not entity:
                    return DomainError.not_found("MemoryEntity", f"{session_id}/{name}")

                return DomainSuccess.create(data=self._to_dto(entity))

        except Exception as e:
            return DomainError.operation_failed("get_memory_entity_by_session_and_name", str(e))

    def list_by_session(
        self,
        session_id: str,
        entity_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> DomainResult[List[MemoryEntityDTO]]:
        """List memory entities for a session."""
        try:
            with self.orm_manager.get_session() as session:
                query = select(MemoryEntity).where(MemoryEntity.session_id == session_id)

                if entity_type:
                    query = query.where(MemoryEntity.entity_type == entity_type)

                query = query.order_by(MemoryEntity.created_at.asc())

                if limit:
                    query = query.limit(limit)

                entities = session.execute(query).scalars().all()
                return DomainSuccess.create(data=[self._to_dto(e) for e in entities])

        except Exception as e:
            return DomainError.operation_failed("list_memory_entities_by_session", str(e))

    def update(self, entity_id: str, updates: Dict[str, Any]) -> DomainResult[MemoryEntityDTO]:
        """Update a memory entity."""
        try:
            with self.orm_manager.get_session() as session:
                entity = session.execute(
                    select(MemoryEntity).where(MemoryEntity.id == entity_id)
                ).scalar_one_or_none()

                if not entity:
                    return DomainError.not_found("MemoryEntity", entity_id)

                for field, value in updates.items():
                    if field == "observations":
                        entity.set_observations(value)
                    elif field == "metadata":
                        entity.set_metadata(value)
                    elif hasattr(entity, field) and field not in ("id", "session_id", "created_at"):
                        setattr(entity, field, value)

                session.flush()
                return DomainSuccess.create(data=self._to_dto(entity))

        except Exception as e:
            return DomainError.operation_failed("update_memory_entity", str(e))

    def delete(self, entity_id: str) -> DomainResult[Dict[str, Any]]:
        """Delete a memory entity."""
        try:
            with self.orm_manager.get_session() as session:
                entity = session.execute(
                    select(MemoryEntity).where(MemoryEntity.id == entity_id)
                ).scalar_one_or_none()

                if not entity:
                    return DomainError.not_found("MemoryEntity", entity_id)

                session.delete(entity)
                session.flush()

                return DomainSuccess.create(
                    data={
                        "entity_id": entity_id,
                        "message": f"MemoryEntity '{entity_id}' deleted successfully",
                    }
                )

        except Exception as e:
            return DomainError.operation_failed("delete_memory_entity", str(e))

    def add_observation(self, entity_id: str, observation: str) -> DomainResult[MemoryEntityDTO]:
        """Add an observation to a memory entity."""
        try:
            with self.orm_manager.get_session() as session:
                entity = session.execute(
                    select(MemoryEntity).where(MemoryEntity.id == entity_id)
                ).scalar_one_or_none()

                if not entity:
                    return DomainError.not_found("MemoryEntity", entity_id)

                entity.add_observation(observation)
                session.flush()

                return DomainSuccess.create(data=self._to_dto(entity))

        except Exception as e:
            return DomainError.operation_failed("add_observation", str(e))
