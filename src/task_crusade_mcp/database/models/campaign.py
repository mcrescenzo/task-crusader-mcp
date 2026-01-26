"""
Campaign SQLAlchemy Model.

Represents a campaign - a container for organizing related tasks.
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.orm import relationship

from task_crusade_mcp.database.models.base import (
    CAMPAIGN_STATUS_CONSTRAINT,
    PRIORITY_CONSTRAINT,
    Base,
    generate_id,
    get_current_timestamp,
)


class Campaign(Base):
    """
    Campaign model representing a project or initiative.

    Campaigns are containers that group related tasks. Every task must
    belong to a campaign.
    """

    __tablename__ = "campaigns"

    id: str = Column(String(36), primary_key=True, default=generate_id)
    name: str = Column(String(255), nullable=False, unique=True, index=True)
    description: Optional[str] = Column(Text, nullable=True)
    status: str = Column(String(20), nullable=False, default="planning")
    priority: str = Column(String(20), nullable=False, default="medium")
    metadata_json: Optional[str] = Column("metadata", Text, nullable=True)
    created_at: datetime = Column(DateTime, nullable=False, default=get_current_timestamp)
    updated_at: datetime = Column(
        DateTime, nullable=False, default=get_current_timestamp, onupdate=get_current_timestamp
    )
    completed_at: Optional[datetime] = Column(DateTime, nullable=True)

    # Table-level constraints
    __table_args__ = (
        CAMPAIGN_STATUS_CONSTRAINT,
        PRIORITY_CONSTRAINT,
    )

    # Relationships
    tasks = relationship("Task", back_populates="campaign", cascade="all, delete-orphan")

    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata as dictionary."""
        if not self.metadata_json:
            return {}
        try:
            return json.loads(self.metadata_json)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_metadata(self, metadata: Dict[str, Any]) -> None:
        """Set metadata from dictionary."""
        self.metadata_json = json.dumps(metadata) if metadata else None

    @property
    def title(self) -> Optional[str]:
        """Get title from metadata."""
        return self.get_metadata().get("title")

    @property
    def owner(self) -> Optional[str]:
        """Get owner from metadata."""
        return self.get_metadata().get("owner")

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "metadata": self.get_metadata(),
            "title": self.title,
            "owner": self.owner,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    def __repr__(self) -> str:
        return f"<Campaign(id={self.id!r}, name={self.name!r}, status={self.status!r})>"
