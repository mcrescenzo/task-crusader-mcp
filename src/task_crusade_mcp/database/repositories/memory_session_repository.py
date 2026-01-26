"""
Memory Session Repository.

SQLAlchemy ORM-based repository for memory session operations.
Used internally by task services - not exposed via MCP.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import select

from task_crusade_mcp.database.models.memory import MemorySession
from task_crusade_mcp.database.orm_manager import ORMManager, get_orm_manager
from task_crusade_mcp.domain.entities.memory import MemorySessionDTO
from task_crusade_mcp.domain.entities.result_types import (
    DomainError,
    DomainResult,
    DomainSuccess,
)


class MemorySessionRepository:
    """
    Memory Session repository using SQLAlchemy ORM.

    Provides CRUD operations for memory sessions with proper error handling
    via DomainResult pattern.
    """

    def __init__(self, orm_manager: Optional[ORMManager] = None):
        """Initialize repository with ORM manager."""
        self.orm_manager = orm_manager or get_orm_manager()

    def _to_dto(self, session: MemorySession) -> MemorySessionDTO:
        """Convert MemorySession model to MemorySessionDTO."""
        return MemorySessionDTO(
            id=session.id,
            name=session.name,
            status=session.status,
            workflow_type=session.workflow_type,
            metadata=session.get_metadata(),
            created_at=session.created_at,
            updated_at=session.updated_at,
            completed_at=session.completed_at,
            archived_at=session.archived_at,
        )

    def create(self, session_data: Dict[str, Any]) -> DomainResult[MemorySessionDTO]:
        """Create a new memory session."""
        try:
            with self.orm_manager.get_session() as db_session:
                # Check for duplicate name if provided
                name = session_data.get("name")
                if name:
                    existing = db_session.execute(
                        select(MemorySession).where(MemorySession.name == name)
                    ).scalar_one_or_none()

                    if existing:
                        return DomainError.already_exists("MemorySession", name)

                # Create session
                memory_session = MemorySession(
                    name=name,
                    status=session_data.get("status", "active"),
                    workflow_type=session_data.get("workflow_type"),
                )

                if session_data.get("metadata"):
                    memory_session.set_metadata(session_data["metadata"])

                db_session.add(memory_session)
                db_session.flush()

                return DomainSuccess.create(data=self._to_dto(memory_session))

        except Exception as e:
            return DomainError.operation_failed("create_memory_session", str(e))

    def get(self, session_id: str) -> DomainResult[MemorySessionDTO]:
        """Get memory session by ID."""
        try:
            with self.orm_manager.get_session() as db_session:
                memory_session = db_session.execute(
                    select(MemorySession).where(MemorySession.id == session_id)
                ).scalar_one_or_none()

                if not memory_session:
                    return DomainError.not_found("MemorySession", session_id)

                return DomainSuccess.create(data=self._to_dto(memory_session))

        except Exception as e:
            return DomainError.operation_failed("get_memory_session", str(e))

    def get_by_name(self, name: str) -> DomainResult[MemorySessionDTO]:
        """Get memory session by name."""
        try:
            with self.orm_manager.get_session() as db_session:
                memory_session = db_session.execute(
                    select(MemorySession).where(MemorySession.name == name)
                ).scalar_one_or_none()

                if not memory_session:
                    return DomainError.not_found("MemorySession", name)

                return DomainSuccess.create(data=self._to_dto(memory_session))

        except Exception as e:
            return DomainError.operation_failed("get_memory_session_by_name", str(e))

    def get_or_create(
        self, name: str, workflow_type: Optional[str] = None
    ) -> DomainResult[MemorySessionDTO]:
        """Get existing session by name or create a new one."""
        result = self.get_by_name(name)
        if result.is_success:
            return result

        # Session doesn't exist, create it
        return self.create(
            {
                "name": name,
                "workflow_type": workflow_type,
                "status": "active",
            }
        )

    def list(
        self,
        status: Optional[str] = None,
        workflow_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> DomainResult[List[MemorySessionDTO]]:
        """List memory sessions with optional filtering."""
        try:
            with self.orm_manager.get_session() as db_session:
                query = select(MemorySession)

                if status:
                    query = query.where(MemorySession.status == status)
                if workflow_type:
                    query = query.where(MemorySession.workflow_type == workflow_type)

                query = query.order_by(MemorySession.created_at.desc())

                if limit:
                    query = query.limit(limit)

                sessions = db_session.execute(query).scalars().all()
                return DomainSuccess.create(data=[self._to_dto(s) for s in sessions])

        except Exception as e:
            return DomainError.operation_failed("list_memory_sessions", str(e))

    def update(self, session_id: str, updates: Dict[str, Any]) -> DomainResult[MemorySessionDTO]:
        """Update a memory session."""
        try:
            with self.orm_manager.get_session() as db_session:
                memory_session = db_session.execute(
                    select(MemorySession).where(MemorySession.id == session_id)
                ).scalar_one_or_none()

                if not memory_session:
                    return DomainError.not_found("MemorySession", session_id)

                for field, value in updates.items():
                    if field == "metadata":
                        memory_session.set_metadata(value)
                    elif hasattr(memory_session, field) and field not in ("id", "created_at"):
                        setattr(memory_session, field, value)

                db_session.flush()
                return DomainSuccess.create(data=self._to_dto(memory_session))

        except Exception as e:
            return DomainError.operation_failed("update_memory_session", str(e))

    def delete(self, session_id: str) -> DomainResult[Dict[str, Any]]:
        """Delete a memory session."""
        try:
            with self.orm_manager.get_session() as db_session:
                memory_session = db_session.execute(
                    select(MemorySession).where(MemorySession.id == session_id)
                ).scalar_one_or_none()

                if not memory_session:
                    return DomainError.not_found("MemorySession", session_id)

                db_session.delete(memory_session)
                db_session.flush()

                return DomainSuccess.create(
                    data={
                        "session_id": session_id,
                        "message": f"MemorySession '{session_id}' deleted successfully",
                    }
                )

        except Exception as e:
            return DomainError.operation_failed("delete_memory_session", str(e))
