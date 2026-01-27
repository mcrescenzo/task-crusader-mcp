"""
Memory SQLAlchemy Models.

Contains MemorySession, MemoryEntity, and MemoryTaskAssociation models.
These are used internally for task operations - not exposed via MCP.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from task_crusade_mcp.database.models.base import (
    MEMORY_SESSION_STATUS_CONSTRAINT,
    Base,
    generate_id,
    get_current_timestamp,
)

logger = logging.getLogger(__name__)


class MemorySession(Base):
    """
    Memory Session model.

    Represents a session for organizing related memory entities.
    """

    __tablename__ = "memory_sessions"

    id: str = Column(String(36), primary_key=True, default=generate_id)
    name: Optional[str] = Column(String(255), nullable=True, unique=True, index=True)
    status: str = Column(String(20), nullable=False, default="active")
    workflow_type: Optional[str] = Column(String(100), nullable=True)
    metadata_json: Optional[str] = Column("metadata", Text, nullable=True)
    created_at: datetime = Column(DateTime, nullable=False, default=get_current_timestamp)
    updated_at: datetime = Column(
        DateTime, nullable=False, default=get_current_timestamp, onupdate=get_current_timestamp
    )
    completed_at: Optional[datetime] = Column(DateTime, nullable=True)
    archived_at: Optional[datetime] = Column(DateTime, nullable=True)

    __table_args__ = (MEMORY_SESSION_STATUS_CONSTRAINT,)

    # Relationships
    entities = relationship("MemoryEntity", back_populates="session", cascade="all, delete-orphan")

    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata as dictionary."""
        if not self.metadata_json:
            return {}
        try:
            return json.loads(self.metadata_json)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(
                f"JSON parse error in MemorySession.metadata for {self.id}: {str(e)}",
                extra={"record_id": self.id, "error_type": type(e).__name__},
            )
            return {}

    def set_metadata(self, metadata: Dict[str, Any]) -> None:
        """Set metadata from dictionary."""
        self.metadata_json = json.dumps(metadata) if metadata else None

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "workflow_type": self.workflow_type,
            "metadata": self.get_metadata(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
        }

    def __repr__(self) -> str:
        return f"<MemorySession(id={self.id!r}, name={self.name!r}, status={self.status!r})>"


class MemoryEntity(Base):
    """
    Memory Entity model.

    Represents a knowledge graph node with typed observations.
    Used for storing acceptance criteria, research items, notes, etc.
    """

    __tablename__ = "memory_entities"

    id: str = Column(String(36), primary_key=True, default=generate_id)
    session_id: str = Column(
        String(36), ForeignKey("memory_sessions.id"), nullable=False, index=True
    )
    name: str = Column(String(255), nullable=False, index=True)
    entity_type: str = Column(String(100), nullable=False, index=True)
    observations_json: Optional[str] = Column("observations", Text, nullable=True)
    metadata_json: Optional[str] = Column("metadata", Text, nullable=True)
    created_at: datetime = Column(DateTime, nullable=False, default=get_current_timestamp)
    updated_at: datetime = Column(
        DateTime, nullable=False, default=get_current_timestamp, onupdate=get_current_timestamp
    )

    # Relationships
    session = relationship("MemorySession", back_populates="entities")
    associations = relationship(
        "MemoryTaskAssociation", back_populates="entity", cascade="all, delete-orphan"
    )

    def get_observations(self) -> List[str]:
        """Get observations as list."""
        if not self.observations_json:
            return []
        try:
            return json.loads(self.observations_json)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(
                f"JSON parse error in MemoryEntity.observations for {self.id}: {str(e)}",
                extra={"record_id": self.id, "error_type": type(e).__name__},
            )
            return []

    def set_observations(self, observations: List[str]) -> None:
        """Set observations from list."""
        self.observations_json = json.dumps(observations) if observations else None

    def add_observation(self, observation: str) -> None:
        """Add an observation to the list."""
        observations = self.get_observations()
        observations.append(observation)
        self.set_observations(observations)

    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata as dictionary."""
        if not self.metadata_json:
            return {}
        try:
            return json.loads(self.metadata_json)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(
                f"JSON parse error in MemoryEntity.metadata for {self.id}: {str(e)}",
                extra={"record_id": self.id, "error_type": type(e).__name__},
            )
            return {}

    def set_metadata(self, metadata: Dict[str, Any]) -> None:
        """Set metadata from dictionary."""
        self.metadata_json = json.dumps(metadata) if metadata else None

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary representation."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "name": self.name,
            "entity_type": self.entity_type,
            "observations": self.get_observations(),
            "metadata": self.get_metadata(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<MemoryEntity(id={self.id!r}, name={self.name!r}, type={self.entity_type!r})>"


# Valid association types constraint
ASSOCIATION_TYPE_CONSTRAINT = CheckConstraint(
    "association_type IN ('findings', 'context', 'reference', 'research', 'analysis', "
    "'implementation_note', 'acceptance_criteria', 'risk', 'testing_step')",
    name="check_association_type",
)


class MemoryTaskAssociation(Base):
    """
    Memory Task Association model.

    Links memory entities to tasks and campaigns with typed associations.

    Note: Both task_id and campaign_id use CASCADE delete to prevent orphaned
    associations when parent entities are deleted. This ensures data integrity
    and prevents silent data loss.
    """

    __tablename__ = "memory_task_associations"

    id: str = Column(String(36), primary_key=True, default=generate_id)
    memory_entity_id: str = Column(
        String(36), ForeignKey("memory_entities.id"), nullable=False, index=True
    )
    task_id: Optional[str] = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True)
    campaign_id: Optional[str] = Column(
        String(36), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True, index=True
    )
    association_type: str = Column(String(50), nullable=False, index=True)
    notes: Optional[str] = Column(Text, nullable=True)
    order_index: int = Column(Integer, nullable=False, default=0)
    created_at: datetime = Column(DateTime, nullable=False, default=get_current_timestamp)
    updated_at: datetime = Column(
        DateTime, nullable=False, default=get_current_timestamp, onupdate=get_current_timestamp
    )

    __table_args__ = (
        ASSOCIATION_TYPE_CONSTRAINT,
        CheckConstraint(
            "(task_id IS NOT NULL) OR (campaign_id IS NOT NULL)",
            name="check_association_target",
        ),
    )

    # Relationships
    entity = relationship("MemoryEntity", back_populates="associations")

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary representation."""
        return {
            "id": self.id,
            "memory_entity_id": self.memory_entity_id,
            "task_id": self.task_id,
            "campaign_id": self.campaign_id,
            "association_type": self.association_type,
            "notes": self.notes,
            "order_index": self.order_index,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        target = f"task={self.task_id}" if self.task_id else f"campaign={self.campaign_id}"
        return f"<MemoryTaskAssociation(id={self.id!r}, type={self.association_type!r}, {target})>"
